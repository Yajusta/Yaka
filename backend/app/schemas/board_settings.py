"""Schémas Pydantic pour les paramètres du tableau."""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class BoardSettingsBase(BaseModel):
    """Schéma de base pour les paramètres."""
    setting_key: str
    setting_value: str
    description: Optional[str] = None


class BoardSettingsCreate(BoardSettingsBase):
    """Schéma pour la création d'un paramètre."""
    pass


class BoardSettingsUpdate(BaseModel):
    """Schéma pour la mise à jour d'un paramètre."""
    setting_value: str
    description: Optional[str] = None


class BoardSettingsResponse(BoardSettingsBase):
    """Schéma de réponse pour les paramètres."""
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BoardTitleUpdate(BaseModel):
    """Schéma pour la mise à jour du titre du tableau."""
    title: str