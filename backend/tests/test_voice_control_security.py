"""Pilotage vocal : quota, saturation, erreurs fournisseur, contexte du prompt."""

import json
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import openai
import pytest
from app.models.card import Card
from app.models.kanban_list import KanbanList
from app.models.user import User, UserRole, UserStatus, ViewScope
from app.routers import voice_control as voice_module
from app.routers.cards import router as cards_router
from app.routers.voice_control import router as voice_router
from app.schemas.card import CARD_DESCRIPTION_MAX_LENGTH
from app.services import llm_service
from app.services.llm_service import (
    LLMBusyError,
    LLMNotConfiguredError,
    LLMProviderError,
    LLMService,
    ResponseType,
)
from app.utils.dependencies import get_current_active_user
from app.utils.rate_limit import VOICE_CONTROL_RATE_LIMITS

VOICE_PER_USER = VOICE_CONTROL_RATE_LIMITS[0].amount
FILTER_RESPONSE = json.dumps(
    {"response_type": ResponseType.FILTER.value, "description": "ok", "cards": []}
)


class DummyService:
    """Service LLM factice : aucun appel réseau."""

    error: Exception | None = None

    def analyze_transcript(self, transcript, user_context, response_type):
        if self.error:
            raise self.error
        return FILTER_RESPONSE


def _user(user_id: int = 1) -> User:
    return User(
        id=user_id,
        email=f"user{user_id}@example.com",
        display_name=None,
        role=UserRole.EDITOR,
        status=UserStatus.ACTIVE,
    )


@pytest.fixture
def voice_app(build_test_app, monkeypatch):
    """Routeur vocal avec un utilisateur courant modifiable et un LLM factice."""
    state = SimpleNamespace(user=_user(), service=DummyService())
    monkeypatch.setattr(voice_module, "LLMService", lambda: state.service)
    app = build_test_app(voice_router)
    app.dependency_overrides[get_current_active_user] = lambda: state.user
    state.app = app
    return state


def _client(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    )


async def _post(client):
    return await client.post(
        "/voice-control/", json={"transcript": "mes tâches", "response_type": "filter"}
    )


# --- Quota, saturation, erreurs -------------------------------------------------


async def test_voice_quota_per_user(voice_app, rate_limit_enabled):
    async with _client(voice_app.app) as client:
        for _ in range(VOICE_PER_USER):
            assert (await _post(client)).status_code == 200
        assert (await _post(client)).status_code == 429

        # Compteur propre à chaque utilisateur
        voice_app.user = _user(2)
        assert (await _post(client)).status_code == 200


async def test_voice_saturated_returns_503(voice_app):
    voice_app.service.error = LLMBusyError()
    async with _client(voice_app.app) as client:
        response = await _post(client)
    assert response.status_code == 503


async def test_voice_provider_error_returns_502_without_details(voice_app):
    voice_app.service.error = LLMProviderError("secret interne")
    async with _client(voice_app.app) as client:
        response = await _post(client)
    assert response.status_code == 502
    assert "secret" not in response.text


async def test_voice_not_configured_returns_503(voice_app, monkeypatch):
    def _missing_key():
        raise LLMNotConfiguredError("Clé API OpenAI manquante")

    monkeypatch.setattr(voice_module, "LLMService", _missing_key)
    async with _client(voice_app.app) as client:
        response = await _post(client)
    assert response.status_code == 503


async def test_voice_not_configured_does_not_consume_quota(
    voice_app, monkeypatch, rate_limit_enabled
):
    def _missing_key():
        raise LLMNotConfiguredError("Clé API OpenAI manquante")

    monkeypatch.setattr(voice_module, "LLMService", _missing_key)
    async with _client(voice_app.app) as client:
        for _ in range(VOICE_PER_USER + 1):
            assert (await _post(client)).status_code == 503


async def test_voice_user_context_without_email(voice_app, monkeypatch):
    captured = {}

    class Capture(DummyService):
        def analyze_transcript(self, transcript, user_context, response_type):
            captured["context"] = user_context
            return FILTER_RESPONSE

    voice_app.service = Capture()
    async with _client(voice_app.app) as client:
        assert (await _post(client)).status_code == 200
    assert "@" not in captured["context"]
    assert json.loads(captured["context"])["user_name"] == "Utilisateur #1"


# --- Service LLM ----------------------------------------------------------------


def test_openai_client_has_timeout_and_retries(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    client_cls = MagicMock()
    monkeypatch.setattr(llm_service, "OpenAI", client_cls)
    llm_service._get_openai_client.cache_clear()
    try:
        LLMService()
        LLMService()
    finally:
        llm_service._get_openai_client.cache_clear()
    # Un seul client pour les deux services
    client_cls.assert_called_once()
    kwargs = client_cls.call_args.kwargs
    assert kwargs["timeout"] == llm_service.LLM_TIMEOUT_SECONDS
    assert kwargs["max_retries"] == llm_service.LLM_MAX_RETRIES


def test_missing_api_key_is_not_configured(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(LLMNotConfiguredError):
        LLMService()


def _failing_service(monkeypatch) -> LLMService:
    """Service dont le fournisseur échoue (délai dépassé)."""
    service = LLMService.__new__(LLMService)
    service.model_name = "test-model"
    parse_mock = MagicMock(
        side_effect=openai.APITimeoutError(
            request=httpx.Request("POST", "https://llm.invalid")
        )
    )
    service.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(parse=parse_mock))
    )
    monkeypatch.setattr(
        LLMService, "_build_filter_instructions", lambda self, ctx: "instructions"
    )
    return service


def _analyze(service: LLMService) -> str:
    return service.analyze_transcript(
        "texte", user_context="{}", response_type=ResponseType.FILTER
    )


def test_provider_error_is_raised_not_swallowed(monkeypatch):
    with pytest.raises(LLMProviderError):
        _analyze(_failing_service(monkeypatch))


def test_truncated_model_output_is_empty_result(monkeypatch):
    service = _failing_service(monkeypatch)
    service.client.chat.completions.parse.side_effect = openai.LengthFinishReasonError(
        completion=MagicMock()
    )
    assert _analyze(service) == "{}"


def test_saturated_service_refuses_immediately(monkeypatch):
    slots = threading.BoundedSemaphore(1)
    slots.acquire()
    monkeypatch.setattr(llm_service, "_llm_call_slots", slots)
    with pytest.raises(LLMBusyError):
        _analyze(_failing_service(monkeypatch))


def test_slot_released_after_provider_error(monkeypatch):
    slots = threading.BoundedSemaphore(1)
    monkeypatch.setattr(llm_service, "_llm_call_slots", slots)
    service = _failing_service(monkeypatch)
    for _ in range(2):
        with pytest.raises(LLMProviderError):
            _analyze(service)


@pytest.mark.parametrize("value", ["0", "abc"])
def test_invalid_concurrency_setting_rejected(monkeypatch, value):
    monkeypatch.setenv("LLM_MAX_CONCURRENT_CALLS", value)
    with pytest.raises(ValueError):
        llm_service._positive_int_from_env("LLM_MAX_CONCURRENT_CALLS", 4)


# --- Contexte du prompt ---------------------------------------------------------


@pytest.fixture
def board(integration_session_factory, monkeypatch):
    """Board de test : get_board_db pointe sur la base isolée."""

    @contextmanager
    def _board_db(board_uid=None):
        session = integration_session_factory()
        try:
            yield session
        finally:
            session.close()

    monkeypatch.setattr(llm_service, "get_board_db", _board_db)
    session = integration_session_factory()
    admin = User(email="admin@example.com", role=UserRole.ADMIN, display_name="Admin")
    invited = User(
        email="invite@example.com",
        role=UserRole.EDITOR,
        status=UserStatus.INVITED,
        display_name=None,
    )
    limited = User(
        email="limited@example.com",
        role=UserRole.EDITOR,
        display_name="Limité",
        view_scope=ViewScope.MINE_ONLY,
    )
    kanban_list = KanbanList(name="À faire", order=1)
    session.add_all([admin, invited, limited, kanban_list])
    session.commit()
    ids = SimpleNamespace(
        admin=admin.id, invited=invited.id, limited=limited.id, list=kanban_list.id
    )

    def add_card(title, description=None, assignee_id=None) -> int:
        card = Card(
            title=title,
            description=description,
            list_id=ids.list,
            created_by=ids.admin,
            assignee_id=assignee_id,
        )
        session.add(card)
        session.commit()
        return card.id

    yield SimpleNamespace(ids=ids, add_card=add_card)
    session.close()


def test_prompt_has_no_emails(board):
    board.add_card("Carte invitée", assignee_id=board.ids.invited)

    users = llm_service.get_users()
    tasks = llm_service.get_tasks({"user_id": board.ids.admin})

    assert "@" not in users and "@" not in tasks
    assert f"Utilisateur #{board.ids.invited}" in users
    assert json.loads(tasks)[0]["assignee_name"] == f"Utilisateur #{board.ids.invited}"


def test_get_tasks_without_user_is_empty(board):
    board.add_card("Carte")
    assert json.loads(llm_service.get_tasks(None)) == []
    assert json.loads(llm_service.get_tasks({})) == []
    assert json.loads(llm_service.get_tasks({"user_id": 9999})) == []


def test_get_tasks_applies_view_scope(board):
    board.add_card("Non assignée")
    board.add_card("À moi", assignee_id=board.ids.limited)

    titles = [
        t["title"]
        for t in json.loads(llm_service.get_tasks({"user_id": board.ids.limited}))
    ]
    assert titles == ["À moi"]


def test_get_tasks_context_is_capped(board, monkeypatch):
    monkeypatch.setattr(llm_service, "LLM_CONTEXT_MAX_CARDS", 3)
    for i in range(5):
        board.add_card(f"Carte {i}", description="x" * 5000)

    tasks = json.loads(llm_service.get_tasks({"user_id": board.ids.admin}))
    assert len(tasks) == 3
    assert all(
        len(t["description"]) == llm_service.LLM_DESCRIPTION_MAX_CHARS + 1
        for t in tasks
    )

    monkeypatch.setattr(llm_service, "LLM_CONTEXT_MAX_CHARS", 2500)
    tasks = json.loads(llm_service.get_tasks({"user_id": board.ids.admin}))
    assert len(tasks) == 2


def test_get_tasks_skips_oversized_card_only(board, monkeypatch):
    monkeypatch.setattr(llm_service, "LLM_CONTEXT_MAX_CHARS", 800)
    board.add_card("Petite")
    board.add_card("Énorme", description="x" * 5000)  # la plus récente

    titles = [
        t["title"]
        for t in json.loads(llm_service.get_tasks({"user_id": board.ids.admin}))
    ]
    assert titles == ["Petite"]


def test_get_tasks_keeps_new_unedited_cards(
    board, integration_session_factory, monkeypatch
):
    """Une carte jamais modifiée (updated_at NULL) est classée par sa création."""
    monkeypatch.setattr(llm_service, "LLM_CONTEXT_MAX_CARDS", 1)
    old_id = board.add_card("Ancienne modifiée")
    board.add_card("Nouvelle")
    session = integration_session_factory()
    try:
        old = session.get(Card, old_id)
        old.created_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        old.updated_at = datetime(2021, 1, 1, tzinfo=timezone.utc)
        session.commit()
    finally:
        session.close()

    titles = [
        t["title"]
        for t in json.loads(llm_service.get_tasks({"user_id": board.ids.admin}))
    ]
    assert titles == ["Nouvelle"]


# --- Description de carte (NV2) --------------------------------------------------


TOO_LONG = "x" * (CARD_DESCRIPTION_MAX_LENGTH + 1)


@pytest.fixture
def cards_app(build_test_app, board):
    app = build_test_app(cards_router)
    app.dependency_overrides[get_current_active_user] = lambda: User(
        id=board.ids.admin,
        email="admin@example.com",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    return app


async def test_card_create_description_too_long_returns_422(cards_app, board):
    body = {"title": "Carte", "list_id": board.ids.list, "description": TOO_LONG}
    async with _client(cards_app) as client:
        response = await client.post("/cards/", json=body)
    assert response.status_code == 422


async def test_card_update_description_too_long_returns_422(cards_app, board):
    card_id = board.add_card("Carte", description="court")
    async with _client(cards_app) as client:
        response = await client.put(f"/cards/{card_id}", json={"description": TOO_LONG})
    assert response.status_code == 422


async def test_card_update_keeps_existing_long_description(cards_app, board):
    """Carte antérieure au plafond : la renvoyer inchangée n'empêche pas l'édition."""
    card_id = board.add_card("Carte", description=TOO_LONG)
    async with _client(cards_app) as client:
        response = await client.put(
            f"/cards/{card_id}", json={"title": "Renommée", "description": TOO_LONG}
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Renommée"

        response = await client.put(
            f"/cards/{card_id}", json={"description": TOO_LONG + "y"}
        )
        assert response.status_code == 422
