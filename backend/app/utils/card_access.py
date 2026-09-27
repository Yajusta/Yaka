"""Accès aux cartes selon le périmètre de vue de l'utilisateur (F06)."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models import Card, User
from ..services import card as card_service


def ensure_can_access_card(user: User, card: Card) -> None:
    """Lever une 403 si la carte est hors du périmètre de vue de l'utilisateur."""
    if not card_service.can_access_card(user, card):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé à cette carte",
        )


def get_accessible_card_or_404(db: Session, card_id: int, user: User) -> Card:
    """Récupérer une carte visible par l'utilisateur.

    Lève une 404 si la carte n'existe pas et une 403 si elle est hors de son
    périmètre de vue (même comportement que ``GET /cards/{id}``).
    """
    card = card_service.get_card(db, card_id=card_id)
    if card is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Carte non trouvée"
        )
    ensure_can_access_card(user, card)
    return card
