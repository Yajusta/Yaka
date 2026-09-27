"""Jetons de session : liaison au board, version (révocation) et statut du compte."""

import httpx
from app.models.user import User, UserRole, UserStatus
from app.multi_database import current_board_uid
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.utils.security import create_access_token, create_user_access_token

ADMIN_EMAIL = "admin@yaka.local"
ADMIN_PASSWORD = "Admin-Test1"
USER_EMAIL = "user@example.com"
USER_PASSWORD = "User-Pass123"


class BoardContext:
    """Middleware ASGI de test : fixe le board courant comme BoardContextMiddleware."""

    def __init__(self, app, board_uid):
        self.app = app
        self.board_uid = board_uid

    async def __call__(self, scope, receive, send):
        token = current_board_uid.set(self.board_uid)
        try:
            await self.app(scope, receive, send)
        finally:
            current_board_uid.reset(token)


def _client(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    )


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _get_user(session_factory, email: str) -> User:
    session = session_factory()
    try:
        return session.query(User).filter(User.email == email).one()
    finally:
        session.close()


async def _me_status(client, token: str) -> int:
    return (await client.get("/auth/me", headers=_auth(token))).status_code


async def test_token_from_board_a_rejected_on_board_b(
    build_test_app, seed_admin_user, create_regular_user, login_user
):
    """Même email (et même base ici) : un jeton émis sur un board est refusé ailleurs."""
    seed_admin_user()
    create_regular_user(USER_EMAIL, USER_PASSWORD)
    app_a = build_test_app(auth_router)
    app_a.add_middleware(BoardContext, board_uid="board-a")
    app_b = build_test_app(auth_router)
    app_b.add_middleware(BoardContext, board_uid="board-b")

    async with _client(app_a) as client_a, _client(app_b) as client_b:
        token_a = await login_user(client_a, USER_EMAIL, USER_PASSWORD)
        assert await _me_status(client_a, token_a) == 200
        assert await _me_status(client_b, token_a) == 401


async def test_default_board_token_rejected_on_named_board(
    build_test_app, seed_admin_user, login_user
):
    """Un jeton de la base par défaut n'ouvre pas un board nommé."""
    seed_admin_user()
    app_default = build_test_app(auth_router)
    app_named = build_test_app(auth_router)
    app_named.add_middleware(BoardContext, board_uid="board-a")

    async with _client(app_default) as client, _client(app_named) as named:
        token = await login_user(client, ADMIN_EMAIL, ADMIN_PASSWORD)
        assert await _me_status(client, token) == 200
        assert await _me_status(named, token) == 401


async def test_token_without_board_or_version_rejected(
    async_client_factory, seed_admin_user, integration_session_factory
):
    """Les jetons émis avant T3 (sans claims `uid`/`board`/`ver`) sont refusés."""
    seed_admin_user()
    admin = _get_user(integration_session_factory, ADMIN_EMAIL)
    async with async_client_factory(auth_router) as client:
        legacy = create_access_token(data={"sub": ADMIN_EMAIL})
        assert await _me_status(client, legacy) == 401
        no_ver = create_access_token(
            data={"sub": ADMIN_EMAIL, "uid": admin.id, "board": "yaka"}
        )
        assert await _me_status(client, no_ver) == 401
        assert await _me_status(client, create_user_access_token(admin)) == 200


async def test_logout_revokes_token(async_client_factory, seed_admin_user, login_user):
    seed_admin_user()
    async with async_client_factory(auth_router) as client:
        token = await login_user(client, ADMIN_EMAIL, ADMIN_PASSWORD)
        other_session = await login_user(client, ADMIN_EMAIL, ADMIN_PASSWORD)

        response = await client.post("/auth/logout", headers=_auth(token))
        assert response.status_code == 200
        assert await _me_status(client, token) == 401
        # La déconnexion ferme toutes les sessions du compte
        assert await _me_status(client, other_session) == 401
        # Déconnexion sans jeton valide : refusée
        assert (await client.post("/auth/logout")).status_code == 401


async def test_logout_in_demo_mode_keeps_shared_sessions(
    async_client_factory, seed_admin_user, login_user, monkeypatch
):
    """Mode démo : comptes partagés, une déconnexion ne ferme pas les autres sessions."""
    monkeypatch.setenv("DEMO_MODE", "true")
    seed_admin_user()
    async with async_client_factory(auth_router) as client:
        token = await login_user(client, ADMIN_EMAIL, ADMIN_PASSWORD)
        other_visitor = await login_user(client, ADMIN_EMAIL, ADMIN_PASSWORD)
        response = await client.post("/auth/logout", headers=_auth(token))
        assert response.status_code == 200
        assert await _me_status(client, other_visitor) == 200


async def test_logout_allowed_when_password_change_required(
    async_client_factory, seed_admin_user, integration_session_factory, login_user
):
    seed_admin_user()
    session = integration_session_factory()
    try:
        admin = session.query(User).filter(User.email == ADMIN_EMAIL).one()
        admin.must_change_password = True
        session.commit()
    finally:
        session.close()

    async with async_client_factory(auth_router) as client:
        token = await login_user(client, ADMIN_EMAIL, ADMIN_PASSWORD)
        response = await client.post("/auth/logout", headers=_auth(token))
        assert response.status_code == 200
        assert await _me_status(client, token) == 401


async def test_change_password_returns_usable_token(
    async_client_factory, seed_admin_user, login_user
):
    seed_admin_user()
    async with async_client_factory(auth_router, users_router) as client:
        token = await login_user(client, ADMIN_EMAIL, ADMIN_PASSWORD)
        response = await client.post(
            "/auth/change-password",
            json={"current_password": ADMIN_PASSWORD, "new_password": "New-Pass123"},
            headers=_auth(token),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["email"] == ADMIN_EMAIL
        assert body["token_type"] == "bearer"

        assert await _me_status(client, token) == 401
        assert await _me_status(client, body["access_token"]) == 200
        users = await client.get("/users/", headers=_auth(body["access_token"]))
        assert users.status_code == 200


async def test_password_reset_revokes_token(
    async_client_factory,
    seed_admin_user,
    create_regular_user,
    integration_session_factory,
    login_user,
):
    seed_admin_user()
    create_regular_user(USER_EMAIL, USER_PASSWORD)
    async with async_client_factory(auth_router, users_router) as client:
        token = await login_user(client, USER_EMAIL, USER_PASSWORD)

        await client.post("/auth/request-password-reset", json={"email": USER_EMAIL})
        reset_token = _get_user(integration_session_factory, USER_EMAIL).invite_token
        assert reset_token
        response = await client.post(
            "/users/set-password",
            json={"token": reset_token, "password": "Reset-Pass123"},
        )
        assert response.status_code == 200

        assert await _me_status(client, token) == 401
        await login_user(client, USER_EMAIL, "Reset-Pass123")


async def test_admin_changes_revoke_token(
    async_client_factory,
    seed_admin_user,
    create_regular_user,
    integration_session_factory,
    login_user,
):
    """Mot de passe ou rôle modifié par un admin, suppression : jeton révoqué."""
    seed_admin_user()
    create_regular_user(USER_EMAIL, USER_PASSWORD)
    user_id = _get_user(integration_session_factory, USER_EMAIL).id

    async with async_client_factory(auth_router, users_router) as client:
        admin = _auth(await login_user(client, ADMIN_EMAIL, ADMIN_PASSWORD))

        # Modification sans effet sur les droits : le jeton reste valide
        token = await login_user(client, USER_EMAIL, USER_PASSWORD)
        response = await client.put(
            f"/users/{user_id}", json={"display_name": "Renamed"}, headers=admin
        )
        assert response.status_code == 200
        assert await _me_status(client, token) == 200

        response = await client.put(
            f"/users/{user_id}", json={"role": "visitor"}, headers=admin
        )
        assert response.status_code == 200
        assert await _me_status(client, token) == 401

        token = await login_user(client, USER_EMAIL, USER_PASSWORD)
        response = await client.put(
            f"/users/{user_id}", json={"password": "Admin-Set123"}, headers=admin
        )
        assert response.status_code == 200
        assert await _me_status(client, token) == 401

        token = await login_user(client, USER_EMAIL, "Admin-Set123")
        response = await client.delete(f"/users/{user_id}", headers=admin)
        assert response.status_code == 200
        assert await _me_status(client, token) == 401


async def test_recreated_account_does_not_accept_old_token(
    async_client_factory,
    seed_admin_user,
    create_regular_user,
    integration_session_factory,
    login_user,
):
    """Un compte supprimé puis recréé avec le même email n'hérite pas des jetons."""
    seed_admin_user()
    create_regular_user(USER_EMAIL, USER_PASSWORD)
    old_user = _get_user(integration_session_factory, USER_EMAIL)
    old_token = create_user_access_token(old_user)

    session = integration_session_factory()
    try:
        session.query(User).filter(User.id == old_user.id).update(
            {User.status: UserStatus.DELETED}
        )
        session.commit()
    finally:
        session.close()
    create_regular_user(USER_EMAIL, USER_PASSWORD)

    async with async_client_factory(auth_router) as client:
        assert await _me_status(client, old_token) == 401


async def test_invited_account_rejected(
    async_client_factory, seed_admin_user, integration_session_factory, login_user
):
    seed_admin_user()
    async with async_client_factory(auth_router, users_router) as client:
        admin = _auth(await login_user(client, ADMIN_EMAIL, ADMIN_PASSWORD))
        response = await client.post(
            "/users/invite",
            json={"email": USER_EMAIL, "display_name": "Invité", "role": "editor"},
            headers=admin,
        )
        assert response.status_code == 200

        invited = _get_user(integration_session_factory, USER_EMAIL)
        assert invited.status == UserStatus.INVITED
        assert invited.role == UserRole.EDITOR
        assert await _me_status(client, create_user_access_token(invited)) == 401
