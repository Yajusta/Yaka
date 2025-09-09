"""Schémas Pydantic pour les cartes."""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime, date
from ..models.card import CardPriority
from .label import LabelResponse
from .card_item import CardItemResponse
from .card_comment import CardCommentResponse
from .user import UserResponse


class CardBase(BaseModel):
    """Schéma de base pour les cartes."""

    titre: str = Field(..., min_length=1, max_length=200, description="Titre de la carte")
    description: Optional[str] = Field(None, description="Description de la carte")
    date_echeance: Optional[date] = Field(None, description="Date d'échéance de la carte")
    priorite: CardPriority = Field(CardPriority.MEDIUM, description="Priorité de la carte")
    assignee_id: Optional[int] = Field(None, description="ID de l'utilisateur assigné")


class CardCreate(CardBase):
    """Schéma pour la création d'une carte."""

    list_id: int = Field(..., description="ID de la liste Kanban")
    position: Optional[int] = Field(
        None, ge=0, description="Position dans la liste (optionnel, ajouté à la fin si non spécifié)"
    )
    label_ids: Optional[List[int]] = Field([], description="Liste des IDs des étiquettes")


class CardUpdate(BaseModel):
    """Schéma pour la mise à jour d'une carte."""

    titre: Optional[str] = Field(None, min_length=1, max_length=200, description="Titre de la carte")
    description: Optional[str] = Field(None, description="Description de la carte")
    date_echeance: Optional[date] = Field(None, description="Date d'échéance de la carte")
    priorite: Optional[CardPriority] = Field(None, description="Priorité de la carte")
    list_id: Optional[int] = Field(None, description="ID de la liste Kanban")
    position: Optional[int] = Field(None, ge=0, description="Position dans la liste")
    assignee_id: Optional[int] = Field(None, description="ID de l'utilisateur assigné")
    label_ids: Optional[List[int]] = Field(None, description="Liste des IDs des étiquettes")


class CardListUpdate(BaseModel):
    """Schéma pour la mise à jour de la liste d'une carte."""

    list_id: int = Field(..., description="ID de la nouvelle liste Kanban")


class CardResponse(CardBase):
    """Schéma de réponse pour les cartes."""

    id: int
    list_id: int
    position: int
    created_by: int
    is_archived: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    labels: List[LabelResponse] = []
    creator: Optional[UserResponse] = None
    assignee: Optional[UserResponse] = None
    items: List[CardItemResponse] = []
    comments: List[CardCommentResponse] = []

    class Config:
        from_attributes = True


class CardFilter(BaseModel):
    """Schéma pour les filtres de cartes."""

    list_id: Optional[int] = Field(None, description="ID de la liste Kanban")
    assignee_id: Optional[int] = Field(None, description="ID de l'utilisateur assigné")
    priorite: Optional[CardPriority] = Field(None, description="Priorité de la carte")
    label_id: Optional[int] = Field(None, description="ID de l'étiquette")
    search: Optional[str] = Field(None, description="Terme de recherche")
    include_archived: bool = Field(False, description="Inclure les cartes archivées")


class CardMoveRequest(BaseModel):
    """Schéma pour le déplacement d'une carte entre listes."""

    source_list_id: int = Field(..., description="ID de la liste source")
    target_list_id: int = Field(..., description="ID de la liste de destination")
    position: Optional[int] = Field(None, ge=0, description="Position dans la liste de destination")

    @validator("target_list_id")
    def validate_move_request(cls, v, values):
        """Valide la demande de déplacement."""
        # Permettre le déplacement dans la même liste si une position est spécifiée
        # Cela permet la réorganisation des cartes dans une même colonne
        return v


class BulkCardMoveRequest(BaseModel):
    """Schéma pour le déplacement en masse de cartes."""

    card_ids: List[int] = Field(..., description="Liste des IDs des cartes à déplacer")
    target_list_id: int = Field(..., description="ID de la liste de destination")

    @validator("card_ids")
    def validate_card_ids(cls, v):
        """Valide que la liste des IDs de cartes n'est pas vide et ne contient pas de doublons."""
        if not v:
            raise ValueError("Au moins une carte doit être fournie")

        if len(v) != len(set(v)):
            raise ValueError("Les IDs de cartes doivent être uniques")

        return v
