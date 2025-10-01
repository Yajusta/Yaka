"""Pytest fixtures shared across integration tests to isolate the SQLite database."""

import os
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator, Awaitable, Callable, Iterable

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Allow tests to import the application package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base, get_db
from app.models.user import UserRole
from app.schemas import KanbanListCreate, UserCreate
from app.services.board_settings import initialize_default_settings
from app.services.kanban_list import create_list as service_create_list
from app.services.user import create_admin_user, create_user


@pytest.fixture(scope="session")
def integration_engine(tmp_path_factory: pytest.TempPathFactory):
    """Provide a dedicated SQLite engine per test session."""
    db_file = tmp_path_factory.mktemp("integration_db") / "yaka_integration.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def integration_session_factory(integration_engine) -> sessionmaker:
    """Reset the schema before each test and expose a sessionmaker."""
    Base.metadata.drop_all(bind=integration_engine)
    Base.metadata.create_all(bind=integration_engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=integration_engine)


@pytest.fixture
def build_test_app(integration_session_factory: sessionmaker) -> Callable[..., FastAPI]:
    """Create a FastAPI app wired to the isolated test database."""

    def _build(*routers) -> FastAPI:
        app = FastAPI()
        for router in routers:
            app.include_router(router)

        def override_get_db() -> Iterable[Session]:
            db = integration_session_factory()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        return app

    return _build


@pytest.fixture
def async_client_factory(build_test_app: Callable[..., FastAPI]):
    """Return an async contextmanager that yields an httpx.AsyncClient."""

    @asynccontextmanager
    async def _factory(*routers) -> AsyncIterator[httpx.AsyncClient]:
        app = build_test_app(*routers)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client

    return _factory


@pytest.fixture
def seed_admin_user(integration_session_factory: sessionmaker) -> Callable[[], None]:
    """Bootstrap the default admin user and board settings."""

    def _seed() -> None:
        session = integration_session_factory()
        try:
            create_admin_user(session)
            initialize_default_settings(session)
        finally:
            session.close()

    return _seed


@pytest.fixture
def create_regular_user(integration_session_factory: sessionmaker) -> Callable[[str, str, str | None], None]:
    """Create a regular user in the isolated database."""

    def _create(
        email: str, password: str, display_name: str | None = "Regular", role: UserRole = UserRole.EDITOR
    ) -> None:
        session = integration_session_factory()
        try:
            payload = UserCreate(
                email=email,
                password=password,
                display_name=display_name,
                role=role,
                language="fr",
            )
            create_user(session, payload)
        finally:
            session.close()

    return _create


@pytest.fixture
def create_list_record(integration_session_factory: sessionmaker) -> Callable[[str, int], int]:
    """Utility to seed a Kanban list without going through HTTP endpoints."""

    def _create(name: str, order: int) -> int:
        session = integration_session_factory()
        try:
            list_payload = KanbanListCreate(name=name, order=order)
            created = service_create_list(session, list_payload)
            list_id = created.id
        finally:
            session.close()
        return list_id

    return _create


@pytest.fixture
def login_user() -> Callable[[httpx.AsyncClient, str, str], Awaitable[str]]:
    """Return an async helper to authenticate via /auth/login."""

    async def _login(client: httpx.AsyncClient, username: str, password: str) -> str:
        response = await client.post(
            "/auth/login",
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["token_type"] == "bearer"
        return payload["access_token"]

    return _login


@pytest.fixture(autouse=True)
def disable_email_sending(monkeypatch):
    """Neutralise l'envoi d'emails pour éviter les appels réseau pendant les tests."""

    # Patcher directement au niveau du module pour éviter les timeouts SMTP
    def _noop(*args, **kwargs):
        return None

    # Patcher le module email source
    monkeypatch.setattr("app.services.email.send_mail", _noop)
    monkeypatch.setattr("app.services.email.send_invitation", _noop)
    monkeypatch.setattr("app.services.email.send_password_reset", _noop)

    # Patcher aussi les références locales dans user.py qui importe email as email_service
    monkeypatch.setattr("app.services.user.email_service.send_mail", _noop)
    monkeypatch.setattr("app.services.user.email_service.send_invitation", _noop)
    monkeypatch.setattr("app.services.user.email_service.send_password_reset", _noop)
