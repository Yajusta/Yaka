"""Réinitialisation et invitations : board du lien, échappement, TTL, délai minimal (T4)."""

import datetime
from unittest.mock import patch

import httpx
import pytest
from app.models.user import User, UserRole, UserStatus
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.schemas import UserUpdate
from app.services import user as user_service
from app.services.email import SMTP_TIMEOUT, _board_links, send_mail
from app.services.email_templates import (
    get_invitation_html,
    get_password_reset_html,
    get_password_reset_plain,
)
from app.utils.board_context import BoardContextMiddleware

ADMIN_EMAIL = "admin@yaka.local"
ADMIN_PASSWORD = "Admin-Test1"
USER_EMAIL = "user@example.com"
USER_PASSWORD = "User-Pass123"
EXISTING_BOARD = "team-1"


@pytest.fixture
def sent(monkeypatch):
    """Enregistre les emails envoyés (invitation et réinitialisation)."""
    calls = []

    def _recorder(kind):
        def _send(**kwargs):
            calls.append((kind, kwargs))

        return _send

    monkeypatch.setattr(
        user_service.email_service, "send_password_reset", _recorder("reset")
    )
    monkeypatch.setattr(
        user_service.email_service, "send_invitation", _recorder("invite")
    )
    return calls


@pytest.fixture
def board_client(build_test_app, monkeypatch):
    """Client sur une app montée comme main.py (nu + /board/{uid}) avec le middleware."""
    monkeypatch.setattr(
        BoardContextMiddleware,
        "_board_database_exists",
        lambda self, uid: uid == EXISTING_BOARD,
    )
    app = build_test_app(auth_router, users_router)
    app.include_router(auth_router, prefix="/board/{board_uid}")
    app.include_router(users_router, prefix="/board/{board_uid}")
    app.add_middleware(BoardContextMiddleware)
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    )


def _get_user(session_factory, email: str) -> User:
    session = session_factory()
    try:
        return session.query(User).filter(User.email == email).one()
    finally:
        session.close()


def _age_token(session_factory, email: str, delta: datetime.timedelta) -> str:
    """Vieillit le jeton en attente de `delta` et le renvoie."""
    session = session_factory()
    try:
        user = session.query(User).filter(User.email == email).one()
        user.invited_at = user_service.get_system_timezone_datetime() - delta
        session.commit()
        return user.invite_token
    finally:
        session.close()


# --- F04 : board du lien -----------------------------------------------------


async def test_reset_link_uses_path_board_not_body(
    board_client, seed_admin_user, create_regular_user, sent
):
    seed_admin_user()
    create_regular_user(USER_EMAIL, USER_PASSWORD)
    async with board_client as client:
        response = await client.post(
            f"/board/{EXISTING_BOARD}/auth/request-password-reset",
            json={"email": USER_EMAIL, "board_uid": "evil.example/x?"},
        )
    assert response.status_code == 200
    assert sent == [("reset", sent[0][1])]
    assert sent[0][1]["board_uid"] == EXISTING_BOARD
    assert sent[0][1]["email"] == USER_EMAIL


async def test_body_board_uid_ignored_without_board_path(
    board_client, seed_admin_user, create_regular_user, sent
):
    seed_admin_user()
    create_regular_user(USER_EMAIL, USER_PASSWORD)
    async with board_client as client:
        response = await client.post(
            "/auth/request-password-reset",
            json={"email": USER_EMAIL, "board_uid": "evil.example/x?"},
        )
        # Uid invalide dans le chemin : rejeté par le middleware, aucun email
        invalid = await client.post(
            "/board/evil.example/auth/request-password-reset",
            json={"email": ADMIN_EMAIL},
        )
    assert response.status_code == 200
    assert invalid.status_code == 401
    assert [kwargs["board_uid"] for _, kwargs in sent] == [None]


async def test_unknown_board_refused_without_revealing_account(
    board_client, seed_admin_user, create_regular_user, sent
):
    seed_admin_user()
    create_regular_user(USER_EMAIL, USER_PASSWORD)
    async with board_client as client:
        known = await client.post(
            "/board/missing-board/auth/request-password-reset",
            json={"email": USER_EMAIL},
        )
        unknown = await client.post(
            "/board/missing-board/auth/request-password-reset",
            json={"email": "nobody@example.com"},
        )
    assert known.status_code == unknown.status_code == 401
    assert known.json() == unknown.json()
    assert sent == []


async def test_reset_response_identical_whether_account_exists(
    async_client_factory, seed_admin_user, create_regular_user, sent
):
    seed_admin_user()
    create_regular_user(USER_EMAIL, USER_PASSWORD)
    async with async_client_factory(auth_router) as client:
        known = await client.post(
            "/auth/request-password-reset", json={"email": USER_EMAIL}
        )
        unknown = await client.post(
            "/auth/request-password-reset", json={"email": "nobody@example.com"}
        )
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    assert len(sent) == 1


async def test_invitation_link_ignores_body_board_uid(
    board_client, seed_admin_user, login_user, integration_session_factory, sent
):
    seed_admin_user()
    async with board_client as client:
        token = await login_user(client, ADMIN_EMAIL, ADMIN_PASSWORD)
        admin = {"Authorization": f"Bearer {token}"}
        # Le jeton de l'admin est lié à la base par défaut : on invite sans préfixe
        response = await client.post(
            "/users/invite",
            json={"email": USER_EMAIL, "role": "editor", "board_uid": "evil.example"},
            headers=admin,
        )
        assert response.status_code == 200
        user_id = response.json()["id"]
        _age_token(
            integration_session_factory, USER_EMAIL, datetime.timedelta(minutes=2)
        )
        response = await client.post(
            f"/users/{user_id}/resend-invitation",
            json={"board_uid": "evil.example"},
            headers=admin,
        )
        assert response.status_code == 200
    assert [(kind, kwargs["board_uid"]) for kind, kwargs in sent] == [
        ("invite", None),
        ("invite", None),
    ]


# --- F04 : échappement et encodage ---------------------------------------------


def test_board_uid_and_token_are_encoded_in_links():
    link, board_url = _board_links("a/b?c#d", "tok+/=", "http://x/invite")
    assert "/board/a%2Fb%3Fc%23d/invite?token=tok%2B%2F%3D" in link
    assert board_url.endswith("/board/a%2Fb%3Fc%23d")


def test_html_templates_escape_values_plain_text_does_not():
    name = '<script>alert("x")</script>'
    link = 'https://h/invite?token=t&reset=true"><a href="evil'
    html_body = get_password_reset_html(name, link, "https://h")
    assert "<script>" not in html_body
    assert "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;" in html_body
    assert 'href="https://h/invite?token=t&amp;reset=true&quot;&gt;' in html_body
    assert get_invitation_html(name, link, "https://h").count("<script>") == 0

    plain = get_password_reset_plain(name, link, "https://h")
    assert name in plain
    assert link in plain


def test_placeholders_in_values_are_not_substituted():
    html_body = get_password_reset_html("{{RESET_LINK}}", "https://h/l", "https://h")
    assert "{{RESET_LINK}}" in html_body


# --- F09 : timeout SMTP et délai minimal ---------------------------------------------


@pytest.mark.parametrize("secure, cls", [("starttls", "SMTP"), ("ssl", "SMTP_SSL")])
def test_smtp_timeout(secure, cls):
    # send_mail capturé à l'import (conftest le neutralise dans le module) ;
    # SMTP_SECURE est lu dans les globals de cette fonction.
    with patch.dict(send_mail.__globals__, {"SMTP_SECURE": secure}), patch(
        f"smtplib.{cls}"
    ) as smtp:
        send_mail("to@example.com", "s", "<p>h</p>", "p")
    assert smtp.call_args.kwargs["timeout"] == SMTP_TIMEOUT == 10


async def test_reset_token_not_regenerated_within_delay(
    async_client_factory,
    seed_admin_user,
    create_regular_user,
    integration_session_factory,
    sent,
):
    seed_admin_user()
    create_regular_user(USER_EMAIL, USER_PASSWORD)
    async with async_client_factory(auth_router) as client:
        first = await client.post(
            "/auth/request-password-reset", json={"email": USER_EMAIL}
        )
        token = _get_user(integration_session_factory, USER_EMAIL).invite_token
        second = await client.post(
            "/auth/request-password-reset", json={"email": USER_EMAIL}
        )
        assert first.json() == second.json()
        assert _get_user(integration_session_factory, USER_EMAIL).invite_token == token
        assert len(sent) == 1

        _age_token(
            integration_session_factory, USER_EMAIL, datetime.timedelta(minutes=2)
        )
        await client.post("/auth/request-password-reset", json={"email": USER_EMAIL})
        assert _get_user(integration_session_factory, USER_EMAIL).invite_token != token
        assert len(sent) == 2


# --- F12 : durée de vie ---------------------------------------------------------


async def _set_password(client, token: str) -> int:
    response = await client.post(
        "/users/set-password", json={"token": token, "password": "Reset-Pass123"}
    )
    return response.status_code


async def test_expired_reset_token_rejected_and_cleared(
    async_client_factory,
    seed_admin_user,
    create_regular_user,
    integration_session_factory,
):
    seed_admin_user()
    create_regular_user(USER_EMAIL, USER_PASSWORD)
    async with async_client_factory(auth_router, users_router) as client:
        await client.post("/auth/request-password-reset", json={"email": USER_EMAIL})
        token = _age_token(
            integration_session_factory, USER_EMAIL, datetime.timedelta(minutes=61)
        )
        assert await _set_password(client, token) == 400
    user = _get_user(integration_session_factory, USER_EMAIL)
    assert user.invite_token is None and user.invited_at is None


async def test_reset_token_valid_within_ttl(
    async_client_factory,
    seed_admin_user,
    create_regular_user,
    integration_session_factory,
):
    seed_admin_user()
    create_regular_user(USER_EMAIL, USER_PASSWORD)
    async with async_client_factory(auth_router, users_router) as client:
        await client.post("/auth/request-password-reset", json={"email": USER_EMAIL})
        token = _age_token(
            integration_session_factory, USER_EMAIL, datetime.timedelta(minutes=50)
        )
        assert await _set_password(client, token) == 200


def test_invitation_ttl(integration_session_factory):
    session = integration_session_factory()
    try:
        invited = user_service.invite_user(
            session, USER_EMAIL, "Invité", UserRole.EDITOR
        )
        token = invited.invite_token
        now = user_service.get_system_timezone_datetime()

        # Une invitation reste valide bien au-delà du TTL de réinitialisation
        invited.invited_at = now - datetime.timedelta(days=6)
        session.commit()
        assert user_service.get_user_by_any_token(session, token) is not None

        invited.invited_at = now - datetime.timedelta(days=8)
        session.commit()
        assert user_service.get_user_by_any_token(session, token) is None
        session.refresh(invited)
        assert invited.invite_token is None
        assert invited.status == UserStatus.INVITED
    finally:
        session.close()


# --- F13 : jeton invalidé par un changement de mot de passe -------------------------


async def test_admin_password_change_invalidates_reset_token(
    async_client_factory,
    seed_admin_user,
    create_regular_user,
    integration_session_factory,
    login_user,
):
    seed_admin_user()
    create_regular_user(USER_EMAIL, USER_PASSWORD)
    user_id = _get_user(integration_session_factory, USER_EMAIL).id
    async with async_client_factory(auth_router, users_router) as client:
        await client.post("/auth/request-password-reset", json={"email": USER_EMAIL})
        token = _get_user(integration_session_factory, USER_EMAIL).invite_token
        admin = {
            "Authorization": f"Bearer {await login_user(client, ADMIN_EMAIL, ADMIN_PASSWORD)}"
        }
        response = await client.put(
            f"/users/{user_id}", json={"password": "Admin-Set123"}, headers=admin
        )
        assert response.status_code == 200
        assert await _set_password(client, token) == 400
        await login_user(client, USER_EMAIL, "Admin-Set123")


async def test_change_password_invalidates_reset_token(
    async_client_factory,
    seed_admin_user,
    create_regular_user,
    integration_session_factory,
    login_user,
):
    seed_admin_user()
    create_regular_user(USER_EMAIL, USER_PASSWORD)
    async with async_client_factory(auth_router, users_router) as client:
        await client.post("/auth/request-password-reset", json={"email": USER_EMAIL})
        token = _get_user(integration_session_factory, USER_EMAIL).invite_token
        session_token = await login_user(client, USER_EMAIL, USER_PASSWORD)
        response = await client.post(
            "/auth/change-password",
            json={"current_password": USER_PASSWORD, "new_password": "New-Pass123"},
            headers={"Authorization": f"Bearer {session_token}"},
        )
        assert response.status_code == 200
        assert await _set_password(client, token) == 400


def test_admin_password_on_invited_user_activates_account(integration_session_factory):
    session = integration_session_factory()
    try:
        invited = user_service.invite_user(
            session, USER_EMAIL, "Invité", UserRole.EDITOR
        )
        updated = user_service.update_user(
            session, invited.id, UserUpdate(password="Admin-Set123")
        )
        # Jeton effacé : le compte doit pouvoir se connecter avec ce mot de passe
        assert updated.invite_token is None
        assert updated.status == UserStatus.ACTIVE
        assert user_service.authenticate_user(session, USER_EMAIL, "Admin-Set123")
    finally:
        session.close()


def test_concurrent_issue_replaces_token_once(
    integration_session_factory, create_regular_user, sent
):
    """Deux demandes concurrentes lisent le même état : une seule émet un jeton."""
    create_regular_user(USER_EMAIL, USER_PASSWORD)
    first, second = integration_session_factory(), integration_session_factory()
    try:
        user_a = first.query(User).filter(User.email == USER_EMAIL).one()
        user_b = second.query(User).filter(User.email == USER_EMAIL).one()
        assert user_service.issue_pending_token(first, user_a) is True
        # user_b a été lu avant l'émission : son jeton lu (None) n'est plus en base
        assert user_service.issue_pending_token(second, user_b) is False
        assert user_b.invite_token == user_a.invite_token
        assert len(sent) == 1
    finally:
        first.close()
        second.close()
