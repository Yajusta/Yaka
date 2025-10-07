"""Schémas Pydantic pour les libellés."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LabelBase(BaseModel):
    """Schéma de base pour les libellés."""

    name: str = Field(..., min_length=1, max_length=32, description="Nom du libellé (32 caractères max)")
    color: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$", description="Code hexadécimal (ex: #FF5733)")
    description: Optional[str] = Field(
        default=None, max_length=255, description="Description du libellé (255 caractères max)"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Valide que le nom ne contient pas de caractères dangereux."""
        value = value.strip()
        if not value:
            raise ValueError("Le nom ne peut pas être vide")

        # Prévention contre les injections XSS
        dangerous_chars = ["<", ">", '"', "'", "&"]
        value_lower = value.lower()
        for char in dangerous_chars:
            if char in value_lower:
                raise ValueError("Le nom contient des caractères non autorisés")

        return value


class LabelCreate(LabelBase):
    """Schéma pour la création d'un libellé."""

    pass


class LabelUpdate(BaseModel):
    """Schéma pour la mise à jour d'un libellé."""

    name: Optional[str] = Field(default=None, max_length=32, description="Nom du libellé (32 caractères max)")
    color: Optional[str] = None
    description: Optional[str] = Field(
        default=None, max_length=255, description="Description du libellé (255 caractères max)"
    )


class LabelResponse(LabelBase):
    """Schéma de réponse pour les libellés."""

    id: int
    created_by: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
