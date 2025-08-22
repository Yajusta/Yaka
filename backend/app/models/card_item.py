"""Modèle de données pour les éléments de checklist d'une carte."""

from __future__ import annotations

import datetime
from sqlalchemy import Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column

from ..database import Base


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
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.utcnow)

    # Relations
    card: Mapped["Card"] = relationship("Card", back_populates="items")


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .card import Card
