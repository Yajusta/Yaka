"""Schémas Pydantic pour l'historique des cartes."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .user import UserPublic


class CardHistoryEntryCreate(BaseModel):
    """Entrée d'historique saisie via l'API : la carte et l'auteur sont imposés par le serveur."""

    action: str = Field(
        ..., min_length=1, max_length=100, description="Type d'action effectuée"
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Description détaillée de l'action",
    )


class CardHistoryBase(BaseModel):
    """Schéma de base pour l'historique des cartes.

    Sans contrainte de longueur : les réponses sont construites depuis des lignes
    existantes, les limites ne s'appliquent qu'à la saisie (CardHistoryEntryCreate).
    """

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
    user: Optional[UserPublic] = None

    model_config = ConfigDict(from_attributes=True)
