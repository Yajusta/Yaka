"""Service pour la gestion de l'historique des cartes."""

from sqlalchemy.orm import Session, joinedload
from typing import List
from ..models import CardHistory
from ..schemas import CardHistoryCreate, CardHistoryResponse


def create_card_history_entry(db: Session, card_history: CardHistoryCreate) -> CardHistory:
    """Créer une nouvelle entrée d'historique pour une carte."""
    db_history_entry = CardHistory(
        card_id=card_history.card_id,
        user_id=card_history.user_id,
        action=card_history.action,
        description=card_history.description,
    )

    db.add(db_history_entry)
    db.commit()
    db.refresh(db_history_entry)
    return db_history_entry


def get_card_history(db: Session, card_id: int) -> List[CardHistory]:
    """Récupérer l'historique complet d'une carte trié par date décroissante."""
    return (
        db.query(CardHistory)
        .options(joinedload(CardHistory.user))
        .filter(CardHistory.card_id == card_id)
        .order_by(CardHistory.created_at.desc())
        .all()
    )


def get_card_history_with_users(db: Session, card_id: int) -> List[CardHistory]:
    """Récupérer l'historique d'une carte avec les informations des utilisateurs."""
    return (
        db.query(CardHistory)
        .filter(CardHistory.card_id == card_id)
        .order_by(CardHistory.created_at.desc())
        .all()
    )