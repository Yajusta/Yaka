"""Tests pour les nouvelles fonctionnalites de pilotage vocal et du service LLM."""

import json
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

import pytest
from openai import OpenAI

from app.models.user import User, UserStatus
from app.routers.voice_control import VoiceControlRequest, process_voice_transcript
from app.services.llm_service import (
    LLMService,
    AutoIntentResponse,
    CardEditResponse,
    CardFilterResponse,
    ResponseType,
    UnknownResponse,
)


def _make_service_without_init() -> LLMService:
    """Instancie LLMService sans executer __init__ pour faciliter les tests."""
    service = LLMService.__new__(LLMService)
    service.model_name = "test-model"
    # Client factice pour satisfaire les attributs attendus
    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(parse=MagicMock())))
    service.client = cast(OpenAI, fake_client)
    return service


@pytest.mark.parametrize(
    ("response_type", "expected_format"),
    [
        (ResponseType.AUTO_INTENT, AutoIntentResponse),
        (ResponseType.FILTER, CardFilterResponse),
        (ResponseType.CARD_UPDATE, CardEditResponse),
    ],
)
def test_get_completion_selects_response_format(response_type, expected_format):
    """_get_completion doit selectionner le format de reponse adapte au type attendu."""
    service = _make_service_without_init()
    parse_mock = MagicMock(return_value="parsed")
    service.client.chat.completions.parse = parse_mock  # type: ignore[attr-defined]

    result = service._get_completion("commande", "instructions", response_type=response_type)  # type: ignore[arg-type]

    assert result == "parsed"
    parse_mock.assert_called_once()
    kwargs = parse_mock.call_args.kwargs
    assert kwargs["response_format"] is expected_format
    assert kwargs["model"] == "test-model"


def test_analyze_transcript_auto_intent_routes_to_filter(monkeypatch):
    """En mode AUTO_INTENT, le service doit relancer l'analyse avec les instructions filtre si besoin."""
    service = _make_service_without_init()
    call_sequence: list[tuple[str, ResponseType]] = []

    def fake_analyze(self, transcript, instructions, response_type):
        call_sequence.append((instructions, response_type))
        if response_type == ResponseType.AUTO_INTENT:
            payload = AutoIntentResponse(
                response_type=ResponseType.AUTO_INTENT,
                action=ResponseType.FILTER,
                confidence=0.9,
            )
            return payload.model_dump_json()
        return json.dumps(
            {
                "response_type": ResponseType.FILTER.value,
                "description": "Filtre applique",
                "cards": [{"id": 1}],
            }
        )

    monkeypatch.setattr(LLMService, "_analyze_with_openai", fake_analyze)
    monkeypatch.setattr(LLMService, "_build_filter_instructions", lambda self, ctx: "filter instructions")
    monkeypatch.setattr(LLMService, "_build_card_edit_instructions", lambda self, ctx: "card instructions")

    result = service.analyze_transcript("texte", user_context="{}", response_type=ResponseType.AUTO_INTENT)

    data = json.loads(result)
    assert data["response_type"] == ResponseType.FILTER.value
    assert data["cards"] == [{"id": 1}]
    assert len(call_sequence) == 2
    assert call_sequence[0][1] == ResponseType.AUTO_INTENT
    assert call_sequence[1][1] == ResponseType.FILTER
    assert call_sequence[1][0] == "filter instructions"


def test_analyze_transcript_auto_intent_returns_unknown(monkeypatch):
    """Si l'intention detectee est inconnue, le service retourne la reponse Unknown."""
    service = _make_service_without_init()
    call_sequence: list[ResponseType] = []

    def fake_analyze(self, transcript, instructions, response_type):
        call_sequence.append(response_type)
        payload = AutoIntentResponse(
            response_type=ResponseType.AUTO_INTENT,
            action=ResponseType.UNKNOWN,
            confidence=0.1,
        )
        return payload.model_dump_json()

    monkeypatch.setattr(LLMService, "_analyze_with_openai", fake_analyze)
    monkeypatch.setattr(LLMService, "_build_filter_instructions", lambda *args, **kwargs: pytest.fail("Ne doit pas etre appele"))
    monkeypatch.setattr(LLMService, "_build_card_edit_instructions", lambda *args, **kwargs: pytest.fail("Ne doit pas etre appele"))

    result = service.analyze_transcript("texte", user_context="{}", response_type=ResponseType.AUTO_INTENT)

    data = json.loads(result)
    assert data["response_type"] == UnknownResponse().response_type.value
    assert call_sequence == [ResponseType.AUTO_INTENT]


def test_analyze_transcript_card_update_uses_card_instructions(monkeypatch):
    """Avec un type explicite CARD_UPDATE, seules les instructions correspondantes doivent etre utilisees."""
    service = _make_service_without_init()
    call_sequence: list[tuple[str, ResponseType]] = []

    def fake_analyze(self, transcript, instructions, response_type):
        call_sequence.append((instructions, response_type))
        return json.dumps({"response_type": ResponseType.CARD_UPDATE.value, "title": "Nouvelle tache"})

    monkeypatch.setattr(LLMService, "_analyze_with_openai", fake_analyze)
    monkeypatch.setattr(LLMService, "_build_card_edit_instructions", lambda self, ctx: "card instructions")
    monkeypatch.setattr(LLMService, "_build_filter_instructions", lambda *args, **kwargs: pytest.fail("Instruction filtre inutile"))

    result = service.analyze_transcript("texte", user_context="{}", response_type=ResponseType.CARD_UPDATE)

    data = json.loads(result)
    assert data["response_type"] == ResponseType.CARD_UPDATE.value
    assert call_sequence == [("card instructions", ResponseType.CARD_UPDATE)]


@pytest.mark.asyncio
async def test_process_voice_transcript_forwards_response_type_and_cleans(monkeypatch):
    """Le routeur doit transmettre le type de reponse et nettoyer les doublons retournes par le LLM."""
    captured: dict[str, Any] = {}

    class DummyService:
        def analyze_transcript(self, transcript, user_context, instructions="", response_type=ResponseType.AUTO_INTENT):
            captured["transcript"] = transcript
            captured["user_context"] = user_context
            captured["response_type"] = response_type
            return json.dumps(
                {
                    "response_type": ResponseType.FILTER.value,
                    "description": "Cartes trouvees",
                    "cards": [{"id": 1}, {"id": 2}],
                    "labels": [{"label_id": 42}, {"label_id": 42}],
                    "checklist": [
                        {"item_id": 7, "item_name": "Preparer"},
                        {"item_id": 7, "item_name": "Preparer"},
                    ],
                }
            )

    monkeypatch.setattr("app.routers.voice_control.LLMService", lambda: DummyService())

    request = VoiceControlRequest(transcript="bonjour", response_type=ResponseType.FILTER)
    current_user = User(
        id=3,
        email="tester@example.com",
        display_name="Testeur",
        password_hash="hash",
        status=UserStatus.ACTIVE,
    )

    response = await process_voice_transcript(request, db=MagicMock(), current_user=current_user)
    payload_bytes = bytes(response.body)  # JSONResponse.body peut etre un buffer
    payload = json.loads(payload_bytes.decode("utf-8"))

    assert captured["response_type"] == ResponseType.FILTER
    assert json.loads(captured["user_context"]) == {"user_id": 3, "user_name": "Testeur"}
    assert payload["cards"] == [{"id": 1}, {"id": 2}]
    assert payload["labels"] == [{"label_id": 42}]
    assert payload["checklist"] == [{"item_id": 7, "item_name": "Preparer"}]


def test_voice_control_request_defaults_to_auto_intent():
    """Le modele de requete doit utiliser AUTO_INTENT par defaut."""
    request = VoiceControlRequest(transcript="salut")
    assert request.response_type == ResponseType.AUTO_INTENT
