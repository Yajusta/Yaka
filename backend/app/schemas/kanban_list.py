"""Schémas Pydantic pour les listes Kanban."""

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _validate_name_value(value: str) -> str:
    if not value or not value.strip():
        raise ValueError("Le nom de la liste ne peut pas être vide")

    name = value.strip()
    if len(name) < 1:
        raise ValueError("Le nom de la liste doit contenir au moins 1 caractère")
    if len(name) > 100:
        raise ValueError("Le nom de la liste ne peut pas dépasser 100 caractères")
    if re.search(r"[<>\"']", name):
        raise ValueError("Le nom de la liste contient des caractères non autorisés")
    return name


def _validate_order_value(value: int) -> int:
    if value < 1:
        raise ValueError("L'ordre doit être un nombre entier positif (= 1)")
    if value > 9999:
        raise ValueError("L'ordre ne peut pas dépasser 9999")
    return value


class KanbanListBase(BaseModel):
    """Schéma de base pour les listes Kanban."""

    name: str = Field(..., min_length=1, max_length=100, description="Nom de la liste")
    order: int = Field(..., ge=1, description="Ordre d'affichage de la liste")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _validate_name_value(value)

    @field_validator("order")
    @classmethod
    def validate_order(cls, value: int) -> int:
        return _validate_order_value(value)


class KanbanListCreate(KanbanListBase):
    """Schéma pour la création d'une liste Kanban."""


class KanbanListUpdate(BaseModel):
    """Schéma pour la mise à jour d'une liste Kanban."""

    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Nom de la liste")
    order: Optional[int] = Field(None, ge=1, description="Ordre d'affichage de la liste")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return _validate_name_value(value)

    @field_validator("order")
    @classmethod
    def validate_order(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return value
        return _validate_order_value(value)


class KanbanListResponse(KanbanListBase):
    """Schéma de réponse pour les listes Kanban."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class ListDeletionRequest(BaseModel):
    """Schéma pour la demande de suppression d'une liste avec déplacement des cartes."""

    target_list_id: int = Field(..., description="ID de la liste de destination pour les cartes")

    @field_validator("target_list_id")
    @classmethod
    def validate_target_list_id(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("L'ID de la liste de destination doit être un entier positif")
        return value


class ListReorderRequest(BaseModel):
    """Schéma pour la réorganisation des listes."""

    list_orders: dict[int, int] = Field(..., description="Dictionnaire des ID de listes et leurs nouveaux ordres")

    @field_validator("list_orders")
    @classmethod
    def validate_list_orders(cls, value: dict[int, int]) -> dict[int, int]:
        if not value:
            raise ValueError("Au moins une liste doit être fournie")

        orders = list(value.values())
        if any(order < 1 for order in orders):
            raise ValueError("Tous les ordres doivent être positifs")

        if len(orders) != len(set(orders)):
            raise ValueError("Les ordres doivent être uniques")

        return value
