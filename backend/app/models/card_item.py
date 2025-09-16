"""Modèle de données pour les éléments de checklist d'une carte."""

from __future__ import annotations

import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .helpers import get_system_timezone_datetime


class CardItem(Base):
    """Élément de checklist lié à une carte."""

    __tablename__ = "card_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    card_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cards.id", ondelete="CASCADE"), index=True, nullable=False
    )
    texte: Mapped[str] = mapped_column(String(500), nullable=False)
    is_done: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=get_system_timezone_datetime
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=get_system_timezone_datetime, onupdate=get_system_timezone_datetime
    )

    # Relations
    card: Mapped["Card"] = relationship("Card", back_populates="items")

    PROTECTED_FIELDS: set[str] = {"id", "created_by", "created_at"}


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .card import Card
