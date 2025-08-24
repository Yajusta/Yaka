"""Routeur pour la gestion de l'historique des cartes."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas import CardHistoryCreate, CardHistoryResponse
from ..services import card_history as card_history_service
from ..utils.dependencies import get_current_active_user
from ..models import User

router = APIRouter(prefix="/cards/{card_id}/history", tags=["historique cartes"])


@router.get("/", response_model=List[CardHistoryResponse])
async def get_card_history(
    card_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Récupérer l'historique complet d'une carte."""
    # Vérifier que la carte existe (par le biais du service)
    from ..services import card as card_service

    db_card = card_service.get_card(db, card_id=card_id)
    if db_card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carte non trouvée")

    return card_history_service.get_card_history(db, card_id=card_id)


@router.post("/", response_model=CardHistoryResponse)
async def create_card_history_entry(
    card_id: int,
    history_entry: CardHistoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Ajouter une entrée à l'historique d'une carte."""
    # Vérifier que la carte existe
    from ..services import card as card_service

    db_card = card_service.get_card(db, card_id=card_id)
    if db_card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carte non trouvée")

    return card_history_service.create_card_history_entry(db, history_entry)
