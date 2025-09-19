"""Schémas Pydantic pour les cartes."""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..models.card import CardPriority
from .card_comment import CardCommentResponse
from .card_item import CardItemResponse
from .label import LabelResponse
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
        None,
        ge=0,
        description="Position dans la liste (optionnel, ajouté à la fin si non spécifié)",
    )
    label_ids: List[int] = Field(default_factory=list, description="Liste des IDs des étiquettes")


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

    model_config = ConfigDict(from_attributes=True)

    id: int
    list_id: int
    position: int
    created_by: int
    is_archived: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    labels: List[LabelResponse] = Field(default_factory=list)
    creator: Optional[UserResponse] = None
    assignee: Optional[UserResponse] = None
    items: List[CardItemResponse] = Field(default_factory=list)
    comments: List[CardCommentResponse] = Field(default_factory=list)


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


class BulkCardMoveRequest(BaseModel):
    """Schéma pour le déplacement en masse de cartes."""

    card_ids: List[int] = Field(..., description="Liste des IDs des cartes à déplacer")
    target_list_id: int = Field(..., description="ID de la liste de destination")

    @field_validator("card_ids")
    @classmethod
    def validate_card_ids(cls, value: List[int]) -> List[int]:
        """Valide que la liste des IDs de cartes n'est pas vide et ne contient pas de doublons."""
        if not value:
            raise ValueError("Au moins une carte doit être fournie")

        if len(value) != len(set(value)):
            raise ValueError("Les IDs de cartes doivent être uniques")

        return value
