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


class VoiceControlRequest(BaseModel):
    """Requête de pilotage vocal."""

    instruction: str


@router.post("/")
async def process_voice_instruction(
    request: VoiceControlRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Traiter une instruction vocale et retourner l'action à effectuer en JSON.
    Limite l'instruction aux 500 premiers caractères.
    """

    # Limiter l'instruction aux 1000 premiers caractères
    instruction = request.instruction[:500]

    llm_service = LLMService()
    response_json = llm_service.analyze_transcript(instruction)
    return JSONResponse(content=json.loads(response_json))
