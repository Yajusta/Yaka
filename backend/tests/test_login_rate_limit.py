"""Connexion : limitation de débit (IP, compte), mots de passe longs, temps constant."""

import asyncio
import re

import httpx
import pytest
from app.models.user import UserStatus
from app.multi_database import DEFAULT_BOARD_UID, current_board_uid
from app.routers import auth as auth_module
from app.routers.auth import router as auth_router
from app.services import user as user_service
from app.utils import rate_limit as rate_limit_module
from app.utils import security
from app.utils.rate_limit import (
    ACCOUNT_RATE_LIMITS,
    LOGIN_RATE_LIMIT,
    LOGIN_SCOPE,
    PASSWORD_RESET_RATE_LIMIT,
    RATE_LIMIT_MESSAGE,
    _limit_from_env,
)
from limits import parse, parse_many

USER_EMAIL = "user@example.com"
USER_PASSWORD = "User-Pass123"
LOGIN_PER_IP = parse(LOGIN_RATE_LIMIT).amount
RESET_PER_IP = parse(PASSWORD_RESET_RATE_LIMIT).amount
FAILURES_PER_ACCOUNT = min(item.amount for item in ACCOUNT_RATE_LIMITS)

_BOARD_PATH = re.compile(r"^/board/([a-zA-Z0-9-]{1,50})/")


class PathBoardContext:
    """Fixe le board courant d'après le chemin, comme BoardContextMiddleware."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        match = _BOARD_PATH.match(scope.get("path", ""))
        token = current_board_uid.set(match.group(1) if match else None)
        try:
            await self.app(scope, receive, send)
        finally:
            current_board_uid.reset(token)


@pytest.fixture
def app(build_test_app, seed_admin_user, create_regular_user):
    """Routeur auth monté deux fois (nu et préfixé), comme dans app.main."""
    seed_admin_user()
    create_regular_user(USER_EMAIL, USER_PASSWORD)
    application = build_test_app(auth_router)
    application.include_router(auth_router, prefix="/board/{board_uid}")
    application.add_middleware(PathBoardContext)
    return application


def _client(app, ip: str = "10.0.0.1") -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=(ip, 1234)),
        base_url="http://testserver",
    )


async def _login(client, email, password, prefix=""):
    return await client.post(
        f"{prefix}/auth/login", data={"username": email, "password": password}
    )


async def test_login_ip_limit_shared_between_bare_and_prefixed_routes(
    app, rate_limit_enabled
):
    async with _client(app) as client:
        for i in range(LOGIN_PER_IP):
            prefix = "/board/board-a" if i % 2 else ""
            # Emails distincts : seule la limite par IP entre en jeu
            response = await _login(client, f"u{i}@example.com", "Wrong-Pass1", prefix)
            assert response.status_code == 401
        for prefix in ("", "/board/board-b"):
            response = await _login(client, USER_EMAIL, USER_PASSWORD, prefix)
            assert response.status_code == 429
            assert response.json() == {"detail": RATE_LIMIT_MESSAGE}

    # Une autre IP n'est pas concernée
    async with _client(app, ip="10.0.0.2") as other:
        assert (await _login(other, USER_EMAIL, USER_PASSWORD)).status_code == 200


async def test_login_account_limit_per_board_and_email(app, rate_limit_enabled):
    async with _client(app) as client:
        for i in range(FAILURES_PER_ACCOUNT):
            # La route nue est la base par défaut : même compteur que /board/yaka
            prefix = f"/board/{DEFAULT_BOARD_UID}" if i % 2 else ""
            email = USER_EMAIL.upper() if i % 2 else USER_EMAIL
            response = await _login(client, email, "Wrong-Pass1", prefix)
            assert response.status_code == 401
        # Compte bloqué, même avec le bon mot de passe
        response = await _login(client, USER_EMAIL, USER_PASSWORD)
        assert response.status_code == 429
        assert response.json() == {"detail": RATE_LIMIT_MESSAGE}

    # Depuis une autre IP : toujours bloqué (limite par compte, pas par IP)
    async with _client(app, ip="10.0.0.2") as other:
        assert (await _login(other, USER_EMAIL, USER_PASSWORD)).status_code == 429
        # Même email sur un autre board : compteur distinct
        response = await _login(other, USER_EMAIL, USER_PASSWORD, "/board/board-b")
        assert response.status_code == 200


async def test_login_success_resets_account_failures(app, rate_limit_enabled):
    for round_ in range(2):
        async with _client(app, ip=f"10.0.1.{round_}") as client:
            for _ in range(FAILURES_PER_ACCOUNT - 1):
                response = await _login(client, USER_EMAIL, "Wrong-Pass1")
                assert response.status_code == 401
            assert (await _login(client, USER_EMAIL, USER_PASSWORD)).status_code == 200


async def test_password_reset_ip_limit(app, rate_limit_enabled):
    async with _client(app) as client:
        for i in range(RESET_PER_IP):
            prefix = "/board/board-a" if i % 2 else ""
            response = await client.post(
                f"{prefix}/auth/request-password-reset",
                json={"email": f"u{i}@example.com"},
            )
            assert response.status_code == 200
        response = await client.post(
            "/auth/request-password-reset", json={"email": USER_EMAIL}
        )
        assert response.status_code == 429
        assert response.json() == {"detail": RATE_LIMIT_MESSAGE}


async def test_rate_limit_disabled_by_default_in_tests(app):
    async with _client(app) as client:
        for _ in range(LOGIN_PER_IP + 1):
            response = await _login(client, USER_EMAIL, "Wrong-Pass1")
            assert response.status_code == 401


async def test_password_longer_than_72_bytes_is_rejected_with_401(app):
    long_password = "é" * 40  # 80 octets en UTF-8
    async with _client(app) as client:
        for email in (USER_EMAIL, "unknown@example.com"):
            response = await _login(client, email, long_password)
            assert response.status_code == 401


async def test_change_password_with_long_current_password_is_400(app, login_user):
    async with _client(app) as client:
        token = await login_user(client, USER_EMAIL, USER_PASSWORD)
        response = await client.post(
            "/auth/change-password",
            json={"current_password": "a" * 100, "new_password": "New-Pass1234"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400


@pytest.mark.parametrize("status", [None, UserStatus.INVITED, UserStatus.DELETED])
def test_bcrypt_runs_for_unknown_or_inactive_user(
    monkeypatch, integration_session_factory, create_regular_user, status
):
    """Le temps de réponse ne révèle pas l'existence du compte."""
    create_regular_user(USER_EMAIL, USER_PASSWORD)
    session = integration_session_factory()
    try:
        email = "nobody@example.com"
        if status is not None:
            user = user_service.get_user_by_email(session, USER_EMAIL)
            user.status = status
            session.commit()
            email = USER_EMAIL
        calls = []
        real_checkpw = security.bcrypt.checkpw

        def counting_checkpw(*args, **kwargs):
            calls.append(1)
            return real_checkpw(*args, **kwargs)

        monkeypatch.setattr(security.bcrypt, "checkpw", counting_checkpw)
        assert user_service.authenticate_user(session, email, USER_PASSWORD) is None
        assert len(calls) == 1
    finally:
        session.close()


def test_bcrypt_handlers_run_off_the_event_loop():
    """Handlers synchrones : FastAPI les exécute dans le pool de threads."""
    assert not asyncio.iscoroutinefunction(auth_module.login)
    assert not asyncio.iscoroutinefunction(auth_module.change_password)
    assert not asyncio.iscoroutinefunction(auth_module.request_password_reset)


async def test_account_attempt_counted_before_password_check(
    app, rate_limit_enabled, monkeypatch
):
    """Tentative comptée avant bcrypt : des requêtes parallèles ne passent pas
    toutes un contrôle fait sur un compteur encore à zéro."""
    real_authenticate = user_service.authenticate_user
    seen = []

    def spy(db, email, password):
        # Quota déjà consommé au moment de la vérification du mot de passe
        seen.append(
            rate_limit_enabled.limiter.get_window_stats(
                ACCOUNT_RATE_LIMITS[0], LOGIN_SCOPE, DEFAULT_BOARD_UID, email
            ).remaining
        )
        return real_authenticate(db, email, password)

    monkeypatch.setattr(auth_module.user_service, "authenticate_user", spy)
    async with _client(app) as client:
        assert (await _login(client, USER_EMAIL, "Wrong-Pass1")).status_code == 401
    assert seen == [FAILURES_PER_ACCOUNT - 1]


_WRONG_CHANGE = {"current_password": "Wrong-Pass1", "new_password": "New-Pass1234"}


async def _token(app, login_user, email, password=USER_PASSWORD):
    async with _client(app, ip="10.0.2.1") as client:
        return await login_user(client, email, password)


async def test_change_password_ip_limit(
    app, login_user, create_regular_user, rate_limit_enabled
):
    # Plusieurs comptes : seule la limite par IP entre en jeu
    per_user = FAILURES_PER_ACCOUNT - 1
    users = [USER_EMAIL]
    for i in range(1, -(-LOGIN_PER_IP // per_user)):
        users.append(f"cp{i}@example.com")
        create_regular_user(users[-1], USER_PASSWORD)
    headers = [
        {"Authorization": f"Bearer {await _token(app, login_user, email)}"}
        for email in users
    ]
    async with _client(app) as client:
        for i in range(LOGIN_PER_IP):
            prefix = f"/board/{DEFAULT_BOARD_UID}" if i % 2 else ""
            response = await client.post(
                f"{prefix}/auth/change-password",
                json=_WRONG_CHANGE,
                headers=headers[i // per_user],
            )
            assert response.status_code == 400
        response = await client.post(
            "/auth/change-password", json=_WRONG_CHANGE, headers=headers[-1]
        )
        assert response.status_code == 429


async def test_change_password_user_limit_across_ips(
    app, login_user, rate_limit_enabled
):
    """Un jeton volé ne permet pas de répartir les essais sur plusieurs IP."""
    headers = {"Authorization": f"Bearer {await _token(app, login_user, USER_EMAIL)}"}
    for i in range(FAILURES_PER_ACCOUNT):
        async with _client(app, ip=f"10.0.3.{i}") as client:
            response = await client.post(
                "/auth/change-password", json=_WRONG_CHANGE, headers=headers
            )
            assert response.status_code == 400
    async with _client(app, ip="10.0.3.99") as client:
        response = await client.post(
            "/auth/change-password",
            json={"current_password": USER_PASSWORD, "new_password": "New-Pass1234"},
            headers=headers,
        )
        assert response.status_code == 429
        assert response.json() == {"detail": RATE_LIMIT_MESSAGE}


async def test_change_password_success_resets_user_failures(
    app, login_user, rate_limit_enabled
):
    password = USER_PASSWORD
    for round_, new_password in enumerate(("New-Pass1234", "Newer-Pass1234")):
        token = await _token(app, login_user, USER_EMAIL, password)
        headers = {"Authorization": f"Bearer {token}"}
        async with _client(app, ip=f"10.0.4.{round_}") as client:
            for _ in range(FAILURES_PER_ACCOUNT - 1):
                response = await client.post(
                    "/auth/change-password", json=_WRONG_CHANGE, headers=headers
                )
                assert response.status_code == 400
            response = await client.post(
                "/auth/change-password",
                json={"current_password": password, "new_password": new_password},
                headers=headers,
            )
            assert response.status_code == 200
        password = new_password


def test_invalid_limit_in_env_fails_fast(monkeypatch):
    monkeypatch.setenv("LOGIN_RATE_LIMIT", "10/min")
    with pytest.raises(ValueError, match="LOGIN_RATE_LIMIT"):
        _limit_from_env("LOGIN_RATE_LIMIT", "10/minute")
    monkeypatch.setenv("LOGIN_RATE_LIMIT", "")
    assert _limit_from_env("LOGIN_RATE_LIMIT", "10/minute") == "10/minute"
    monkeypatch.setenv("LOGIN_RATE_LIMIT", "10/minute;oops")
    with pytest.raises(ValueError, match="LOGIN_RATE_LIMIT"):
        _limit_from_env("LOGIN_RATE_LIMIT", "10/minute")


async def test_every_account_limit_applies(app, rate_limit_enabled, monkeypatch):
    """Plusieurs limites par compte ("a;b") : aucune n'est ignorée."""
    monkeypatch.setattr(
        rate_limit_module,
        "ACCOUNT_RATE_LIMITS",
        parse_many("100 per 15 minutes;2/day"),
    )
    async with _client(app) as client:
        for _ in range(2):
            assert (await _login(client, USER_EMAIL, "Wrong-Pass1")).status_code == 401
        assert (await _login(client, USER_EMAIL, USER_PASSWORD)).status_code == 429
