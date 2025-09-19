"""Schémas Pydantic pour les éléments de checklist de carte."""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime


class CardItemBase(BaseModel):
    text: str = Field(..., min_length=1, max_length=500, description="Texte de l'élément")
    is_done: bool = Field(False, description="Statut de l'élément")


class CardItemCreate(CardItemBase):
    card_id: int = Field(..., description="ID de la carte")
    position: Optional[int] = Field(None, ge=0, description="Position de l'élément")


class CardItemUpdate(BaseModel):
    text: Optional[str] = Field(None, min_length=1, max_length=500)
    is_done: Optional[bool] = None
    position: Optional[int] = Field(None, ge=0)


class CardItemResponse(CardItemBase):
    id: int
    card_id: int
    position: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

