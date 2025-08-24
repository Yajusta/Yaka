"""Schémas Pydantic pour l'historique des cartes."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from .user import UserResponse


class CardHistoryBase(BaseModel):
    """Schéma de base pour l'historique des cartes."""

    card_id: int = Field(..., description="ID de la carte")
    user_id: int = Field(..., description="ID de l'utilisateur qui a effectué l'action")
    action: str = Field(..., description="Type d'action effectuée")
    description: str = Field(..., description="Description détaillée de l'action")


class CardHistoryCreate(CardHistoryBase):
    """Schéma pour la création d'une entrée d'historique."""


class CardHistoryResponse(CardHistoryBase):
    """Schéma de réponse pour l'historique des cartes."""

    id: int
    created_at: Optional[datetime] = None
    user: Optional[UserResponse] = None

    class Config:
        from_attributes = True