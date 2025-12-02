"""Modèle de données pour l'historique des cartes."""

from __future__ import annotations

import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .helpers import get_system_timezone_datetime


class CardHistory(Base):
    """Modèle de données pour l'historique des actions sur les cartes."""

    __tablename__ = "card_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    card_id: Mapped[int] = mapped_column(Integer, ForeignKey("cards.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), default=get_system_timezone_datetime
    )

    # Relations
    card: Mapped["Card"] = relationship("Card", back_populates="history")
    user: Mapped["User"] = relationship("User", back_populates="card_actions")


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .card import Card
    from .user import User
