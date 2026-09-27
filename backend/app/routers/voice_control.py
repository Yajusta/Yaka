"""Routeur pour le pilotage par la voix."""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..models import User
from ..multi_database import get_dynamic_db as get_db
from ..services.llm_service import (
    LLMBusyError,
    LLMNotConfiguredError,
    LLMProviderError,
    LLMService,
    ResponseType,
    user_label,
)
from ..utils.dependencies import get_current_active_user
from ..utils.rate_limit import (
    VOICE_CONTROL_RATE_LIMITS,
    VOICE_CONTROL_SCOPE,
    consume_account_attempt,
)

router = APIRouter(prefix="/voice-control", tags=["voice-control"])


def _clean_response_data(data: dict) -> dict:
    """
    Nettoie les données de réponse en dédoublonnant les labels et les éléments de checklist.

    Args:
        data: Dictionnaire contenant la réponse du LLM

    Returns:
        Dictionnaire nettoyé
    """
    if not isinstance(data, dict):
        return data

    # Dédoublonner les labels par label_id
    if "labels" in data and isinstance(data["labels"], list):
        seen_label_ids = set()
        unique_labels = []
        for label in data["labels"]:
            if isinstance(label, dict) and "label_id" in label:
                label_id = label["label_id"]
                if label_id not in seen_label_ids:
                    seen_label_ids.add(label_id)
                    unique_labels.append(label)
            else:
                # Garder les labels sans ID (au cas où)
                unique_labels.append(label)
        data["labels"] = unique_labels

    # Dédoublonner les éléments de checklist par item_name (ou item_id s'il existe)
    if "checklist" in data and isinstance(data["checklist"], list):
        seen_items = set()
        unique_checklist = []
        for item in data["checklist"]:
            if isinstance(item, dict):
                # Utiliser item_id s'il existe, sinon item_name
                if "item_id" in item and item["item_id"]:
                    item_key = ("id", item["item_id"])
                elif "item_name" in item:
                    item_key = ("name", item["item_name"])
                else:
                    # Garder les items sans identifiant
                    unique_checklist.append(item)
                    continue

                if item_key not in seen_items:
                    seen_items.add(item_key)
                    unique_checklist.append(item)
            else:
                unique_checklist.append(item)
        data["checklist"] = unique_checklist

    return data


class VoiceControlRequest(BaseModel):
    """Requête de pilotage vocal."""

    transcript: str
    response_type: ResponseType = ResponseType.AUTO_INTENT


@router.post("/")
def process_voice_transcript(
    payload: VoiceControlRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Traiter une instruction vocale et retourner l'action à effectuer en JSON.
    Limite l'instruction aux 500 premiers caractères.

    Handler synchrone : les appels au LLM (bloquants) tournent dans le pool de
    threads, pas sur la boucle d'événements. Le nombre d'appels simultanés est
    borné ; au-delà, 503 immédiat plutôt qu'une file d'attente. Quota par
    utilisateur (board + id) : 429 au-delà.
    """
    # Fonction désactivée : 503 sans consommer le quota
    try:
        llm_service = LLMService()
    except LLMNotConfiguredError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pilotage vocal non configuré",
        )

    consume_account_attempt(
        VOICE_CONTROL_SCOPE, str(current_user.id), VOICE_CONTROL_RATE_LIMITS
    )

    transcript = payload.transcript[:500]

    # Préparer le contexte utilisateur au format JSON (jamais l'email)
    user_context = json.dumps(
        {
            "user_id": current_user.id,
            "user_name": user_label(current_user),
        },
        ensure_ascii=False,
    )

    # Libérer la connexion de la requête pendant l'appel au LLM (jusqu'à
    # plusieurs dizaines de secondes) ; le service ouvre ses propres sessions
    db.close()

    try:
        response_json = llm_service.analyze_transcript(
            transcript=transcript,
            user_context=user_context,
            response_type=payload.response_type,
        )
    except LLMBusyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service vocal saturé, réessayez dans quelques instants",
        )
    except LLMProviderError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Le service d'analyse vocale est indisponible",
        )

    # Nettoyer l'objet de réponse
    response_data = json.loads(response_json)
    response_data = _clean_response_data(response_data)

    return JSONResponse(content=response_data)
