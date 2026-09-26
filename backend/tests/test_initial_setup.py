"""Tests de l'installation neuve et des comptes par défaut (F02)."""

import logging
from contextlib import contextmanager

import pytest
from app.database import Base
from app.models import User, UserRole, UserStatus
from app.routers import auth_router, users_router
from app.schemas import UserCreate
from app.services.user import create_admin_user, create_user
from app.utils import demo_reset
from app.utils.security import get_password_hash, verify_password
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def board_db(integration_session_factory, monkeypatch):
    """Redirige get_board_db de demo_reset vers la base de test isolée."""

    @contextmanager
    def _board_db(board_uid=None):
        db = integration_session_factory()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(demo_reset, "get_board_db", _board_db)
    return integration_session_factory


def _create_admin_with_random_password(session_factory, monkeypatch, caplog):
    """Crée l'admin initial sans DEFAULT_ADMIN_PASSWORD et renvoie le mot de passe logué."""
    monkeypatch.delenv("DEFAULT_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("DEMO_MODE", raising=False)
    session = session_factory()
    try:
        with caplog.at_level(logging.WARNING, logger="app.services.user"):
            create_admin_user(session)
    finally:
        session.close()
    records = [r for r in caplog.records if r.name == "app.services.user"]
    assert len(records) == 1
    assert records[0].levelno == logging.WARNING
    return records[0].args[1]


def test_fresh_install_outside_demo_creates_only_admin(board_db, monkeypatch):
    monkeypatch.delenv("DEMO_MODE", raising=False)

    demo_reset.setup_fresh_database()

    session = board_db()
    try:
        users = session.query(User).all()
        assert [u.email for u in users] == ["admin@yaka.local"]
    finally:
        session.close()


def test_fresh_install_in_demo_mode_creates_demo_accounts(board_db, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.delenv("DEFAULT_ADMIN_PASSWORD", raising=False)

    demo_reset.setup_fresh_database()

    session = board_db()
    try:
        assert session.query(User).count() == 6
        admin = session.query(User).filter(User.email == "admin@yaka.local").one()
        assert verify_password("Admin123", admin.password_hash)
        assert admin.must_change_password is False
    finally:
        session.close()


def test_random_admin_password_is_logged_once_and_must_be_changed(
    integration_session_factory, monkeypatch, caplog
):
    password = _create_admin_with_random_password(
        integration_session_factory, monkeypatch, caplog
    )

    session = integration_session_factory()
    try:
        admin = session.query(User).one()
        assert admin.must_change_password is True
        assert verify_password(password, admin.password_hash)
        assert not verify_password("Admin123", admin.password_hash)
    finally:
        session.close()


def test_default_admin_password_is_used_without_forced_change(
    integration_session_factory, monkeypatch
):
    monkeypatch.setenv("DEFAULT_ADMIN_PASSWORD", "Chosen-Pass1")
    session = integration_session_factory()
    try:
        admin = create_admin_user(session)
        assert verify_password("Chosen-Pass1", admin.password_hash)
        assert admin.must_change_password is False
    finally:
        session.close()


def test_invalid_default_admin_password_raises(board_db, monkeypatch):
    monkeypatch.setenv("DEFAULT_ADMIN_PASSWORD", "weak")
    monkeypatch.delenv("DEMO_MODE", raising=False)

    with pytest.raises(ValueError, match="DEFAULT_ADMIN_PASSWORD"):
        demo_reset.setup_fresh_database()

    session = board_db()
    try:
        assert session.query(User).count() == 0
    finally:
        session.close()


async def test_password_change_required_blocks_api_until_changed(
    integration_session_factory, async_client_factory, login_user, monkeypatch, caplog
):
    password = _create_admin_with_random_password(
        integration_session_factory, monkeypatch, caplog
    )

    async with async_client_factory(auth_router, users_router) as client:
        token = await login_user(client, "admin@yaka.local", password)
        headers = {"Authorization": f"Bearer {token}"}

        blocked = await client.get("/users/", headers=headers)
        assert blocked.status_code == 403
        assert blocked.json()["detail"] == "password_change_required"

        me = await client.get("/auth/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["must_change_password"] is True

        wrong = await client.post(
            "/auth/change-password",
            json={"current_password": "Wrong-Pass1", "new_password": "New-Pass123"},
            headers=headers,
        )
        assert wrong.status_code == 400

        same = await client.post(
            "/auth/change-password",
            json={"current_password": password, "new_password": password},
            headers=headers,
        )
        assert same.status_code == 400

        weak = await client.post(
            "/auth/change-password",
            json={"current_password": password, "new_password": "weakpass"},
            headers=headers,
        )
        assert weak.status_code == 422

        # Au-delà de 72 octets (limite bcrypt) : 422, pas une erreur de hachage
        too_long = await client.post(
            "/auth/change-password",
            json={"current_password": password, "new_password": "Aa1" + "é" * 35},
            headers=headers,
        )
        assert too_long.status_code == 422

        changed = await client.post(
            "/auth/change-password",
            json={"current_password": password, "new_password": "New-Pass123"},
            headers=headers,
        )
        assert changed.status_code == 200
        assert changed.json()["must_change_password"] is False

        allowed = await client.get("/users/", headers=headers)
        assert allowed.status_code == 200

        # Le nouveau mot de passe est effectif
        await login_user(client, "admin@yaka.local", "New-Pass123")


def test_secure_default_accounts_disables_demo_accounts_with_public_password(
    integration_session_factory,
):
    session = integration_session_factory()
    try:
        for email in demo_reset.DEMO_USER_EMAILS:
            create_user(
                session,
                UserCreate(
                    email=email,
                    password=demo_reset.DEMO_USER_PASSWORD,
                    role=UserRole.VISITOR,
                ),
            )
        # Compte démo dont le mot de passe a été changé : conservé
        editor = session.query(User).filter(User.email == "editor@yaka.local").one()
        editor.password_hash = get_password_hash("Other-Pass1")
        session.commit()
        create_user(
            session,
            UserCreate(
                email="admin@yaka.local", password="Admin123", role=UserRole.ADMIN
            ),
        )

        changes = demo_reset.secure_default_accounts(session)

        statuses = {
            u.email: u.status
            for u in session.query(User).filter(
                User.email.in_(demo_reset.DEMO_USER_EMAILS)
            )
        }
        assert statuses.pop("editor@yaka.local") == UserStatus.ACTIVE
        assert set(statuses.values()) == {UserStatus.DELETED}
        assert len(changes) == 5  # 4 comptes démo + admin

        admin = session.query(User).filter(User.email == "admin@yaka.local").one()
        assert admin.must_change_password is True

        # Idempotent
        assert demo_reset.secure_default_accounts(session) == []
    finally:
        session.close()


def test_secure_default_accounts_on_all_boards_logs_warning(
    monkeypatch, caplog, tmp_path
):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    engine = create_engine(f"sqlite:///{data_dir / 'board-1.db'}")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        create_user(
            session,
            UserCreate(
                email="visitor@yaka.local", password=demo_reset.DEMO_USER_PASSWORD
            ),
        )
    finally:
        session.close()
    monkeypatch.chdir(tmp_path)

    try:
        with caplog.at_level(logging.WARNING, logger="app.utils.demo_reset"):
            demo_reset.secure_default_accounts_on_all_boards()

        assert any("visitor@yaka.local" in r.getMessage() for r in caplog.records)
        session = session_factory()
        try:
            visitor = (
                session.query(User).filter(User.email == "visitor@yaka.local").one()
            )
            assert visitor.status == UserStatus.DELETED
        finally:
            session.close()
    finally:
        engine.dispose()


def test_secure_default_accounts_covers_custom_admin_email(
    integration_session_factory, monkeypatch
):
    monkeypatch.setenv("DEFAULT_ADMIN_EMAIL", "boss@example.com")
    session = integration_session_factory()
    try:
        create_user(
            session,
            UserCreate(
                email="boss@example.com", password="Admin123", role=UserRole.ADMIN
            ),
        )

        changes = demo_reset.secure_default_accounts(session)
        assert len(changes) == 1
        assert changes[0].startswith("boss@example.com password reset to ")
    finally:
        session.close()


async def test_public_admin_password_is_replaced_not_just_flagged(
    integration_session_factory, async_client_factory, login_user
):
    """Admin123 ne doit plus permettre ni connexion ni changement de mot de passe."""
    session = integration_session_factory()
    try:
        create_user(
            session,
            UserCreate(
                email="admin@yaka.local", password="Admin123", role=UserRole.ADMIN
            ),
        )
        [change] = demo_reset.secure_default_accounts(session)
        new_password = change.split(" password reset to ")[1].split(" ")[0]
        admin = session.query(User).filter(User.email == "admin@yaka.local").one()
        assert admin.must_change_password is True
        assert not verify_password("Admin123", admin.password_hash)
        assert verify_password(new_password, admin.password_hash)
    finally:
        session.close()

    async with async_client_factory(auth_router, users_router) as client:
        refused = await client.post(
            "/auth/login",
            data={"username": "admin@yaka.local", "password": "Admin123"},
        )
        assert refused.status_code == 401
        # Le mot de passe logué permet de se connecter pour le changer
        await login_user(client, "admin@yaka.local", new_password)


def test_invalid_admin_display_name_names_the_right_variable(
    integration_session_factory, monkeypatch
):
    monkeypatch.setenv("DEFAULT_ADMIN_DISPLAY_NAME", "x" * 100)
    session = integration_session_factory()
    try:
        with pytest.raises(ValueError, match="DEFAULT_ADMIN_DISPLAY_NAME"):
            create_admin_user(session)
    finally:
        session.close()


def test_demo_reset_keeps_users_when_admin_recreation_fails(board_db, monkeypatch):
    """Un échec de recréation de l'admin ne doit pas laisser la base sans utilisateur."""
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.delenv("DEFAULT_ADMIN_PASSWORD", raising=False)
    demo_reset.setup_fresh_database()
    session = board_db()
    try:
        count_before = session.query(User).count()
    finally:
        session.close()
    assert count_before == 6

    monkeypatch.setenv("DEFAULT_ADMIN_PASSWORD", "weak")
    with pytest.raises(ValueError):
        demo_reset.reset_database()

    session = board_db()
    try:
        assert session.query(User).count() == count_before
    finally:
        session.close()


def test_public_default_admin_password_is_ignored_outside_demo(
    integration_session_factory, monkeypatch, caplog
):
    """DEFAULT_ADMIN_PASSWORD=Admin123 (ancienne valeur documentée) : mot de passe aléatoire."""
    monkeypatch.setenv("DEFAULT_ADMIN_PASSWORD", "Admin123")
    monkeypatch.delenv("DEMO_MODE", raising=False)
    session = integration_session_factory()
    try:
        with caplog.at_level(logging.WARNING, logger="app.services.user"):
            admin = create_admin_user(session)
        assert not verify_password("Admin123", admin.password_hash)
        assert admin.must_change_password is True
        # Rien à neutraliser ensuite au démarrage
        assert demo_reset.secure_default_accounts(session) == []
    finally:
        session.close()


def test_secure_default_accounts_resets_demo_account_promoted_to_admin(
    integration_session_factory,
):
    """Un compte démo promu ADMIN (peut-être le seul) n'est pas désactivé."""
    session = integration_session_factory()
    try:
        create_user(
            session,
            UserCreate(
                email="supervisor@yaka.local",
                password=demo_reset.DEMO_USER_PASSWORD,
                role=UserRole.ADMIN,
            ),
        )

        [change] = demo_reset.secure_default_accounts(session)
        assert change.startswith("supervisor@yaka.local password reset to ")
        user = session.query(User).one()
        assert user.status == UserStatus.ACTIVE
        assert user.must_change_password is True
        assert not verify_password(demo_reset.DEMO_USER_PASSWORD, user.password_hash)
    finally:
        session.close()


def test_admin_setting_password_clears_forced_change(
    integration_session_factory, monkeypatch, caplog
):
    from app.schemas import UserUpdate
    from app.services.user import update_user

    _create_admin_with_random_password(integration_session_factory, monkeypatch, caplog)
    session = integration_session_factory()
    try:
        admin = session.query(User).one()
        updated = update_user(session, admin.id, UserUpdate(password="Given-Pass1"))
        assert updated.must_change_password is False
    finally:
        session.close()


async def test_language_can_be_changed_while_password_change_required(
    integration_session_factory, async_client_factory, login_user, monkeypatch, caplog
):
    password = _create_admin_with_random_password(
        integration_session_factory, monkeypatch, caplog
    )

    async with async_client_factory(auth_router, users_router) as client:
        token = await login_user(client, "admin@yaka.local", password)
        response = await client.put(
            "/users/me/language",
            json={"language": "fr"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["language"] == "fr"
