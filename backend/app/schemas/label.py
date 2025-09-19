"""Schémas Pydantic pour les libellés."""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime


class LabelBase(BaseModel):
    """Schéma de base pour les libellés."""
    name: str = Field(..., max_length=32, description="Nom du libellé (32 caractères max)")
    color: str  # Code hexadécimal


class LabelCreate(LabelBase):
    """Schéma pour la création d'un libellé."""
    pass


class LabelUpdate(BaseModel):
    """Schéma pour la mise à jour d'un libellé."""
    name: Optional[str] = Field(None, max_length=32, description="Nom du libellé (32 caractères max)")
    color: Optional[str] = None


class LabelResponse(LabelBase):
    """Schéma de réponse pour les libellés."""
    id: int
    created_by: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


