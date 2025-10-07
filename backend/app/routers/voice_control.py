"""Routeur pour le pilotage par la voix."""

import json
from time import sleep
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..services.llm_service import LLMService

from ..database import get_db
from ..models import User
from ..models.response_model import ChecklistItem, Label, Priority, ResponseModel
from ..utils.dependencies import get_current_active_user

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


@router.post("/")
async def process_voice_transcript(
    request: VoiceControlRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Traiter une instruction vocale et retourner l'action à effectuer en JSON.
    Limite l'instruction aux 500 premiers caractères.
    """

    # Limiter l'instruction aux 1000 premiers caractères
    transcript = request.transcript[:500]

    # Préparer le contexte utilisateur au format JSON
    user_context = json.dumps(
        {"user_id": current_user.id, "user_name": current_user.display_name or current_user.email}, ensure_ascii=False
    )

    llm_service = LLMService()
    response_json = llm_service.analyze_transcript(transcript=transcript, user_context=user_context)

    # Nettoyer l'objet de réponse
    response_data = json.loads(response_json)
    response_data = _clean_response_data(response_data)

    return JSONResponse(content=response_data)
