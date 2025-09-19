"""Schémas Pydantic pour les commentaires de carte."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .user import UserResponse


class CardCommentBase(BaseModel):
    comment: str = Field(..., min_length=1, max_length=1000, description="Texte du commentaire")

    @field_validator("comment")
    @classmethod
    def validate_comment(cls, value: str) -> str:
        """Valide que le commentaire ne contient pas de contenu malveillant."""
        value = value.strip()
        if not value:
            raise ValueError("Le commentaire ne peut pas être vide")

        # Prévention contre les injections XSS et scripts malveillants
        dangerous_patterns = ["<script", "</script>", "javascript:", "<iframe", "</iframe>"]

        value_lower = value.lower()
        for pattern in dangerous_patterns:
            if pattern in value_lower:
                raise ValueError("Le commentaire contient du contenu non autorisé")

        return value


class CardCommentCreate(CardCommentBase):
    card_id: int = Field(..., description="ID de la carte")


class CardCommentUpdate(BaseModel):
    comment: Optional[str] = Field(None, min_length=1, max_length=1000)


class CardCommentResponse(CardCommentBase):
    id: int
    card_id: int
    user_id: int
    is_deleted: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    user: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)
