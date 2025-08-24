"""Modèle de données pour l'historique des cartes."""

from __future__ import annotations

from typing import Optional
import datetime

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Mapped, mapped_column

from ..database import Base


class CardHistory(Base):
    """Modèle de données pour l'historique des actions sur les cartes."""

    __tablename__ = "card_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    card_id: Mapped[int] = mapped_column(Integer, ForeignKey("cards.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relations
    card: Mapped["Card"] = relationship("Card", back_populates="history")
    user: Mapped["User"] = relationship("User", back_populates="card_actions")


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .card import Card
    from .user import User