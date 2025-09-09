"""Schémas Pydantic pour les commentaires de carte."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from .user import UserResponse


class CardCommentBase(BaseModel):
    comment: str = Field(..., min_length=1, max_length=1000, description="Texte du commentaire")


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

    class Config:
        from_attributes = True
