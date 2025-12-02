"""Modèle de données pour les commentaires d'une carte."""

from __future__ import annotations

import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .helpers import get_system_timezone_datetime


class CardComment(Base):
    """Commentaire associé à une carte."""

    __tablename__ = "card_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    card_id: Mapped[int] = mapped_column(Integer, ForeignKey("cards.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=get_system_timezone_datetime
    )
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), default=get_system_timezone_datetime, onupdate=get_system_timezone_datetime
    )

    # Relations
    card: Mapped["Card"] = relationship("Card", back_populates="comments")
    user: Mapped["User"] = relationship("User", back_populates="card_comments")

    PROTECTED_FIELDS: set[str] = {"id", "card_id", "user_id", "created_at"}


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .card import Card
    from .user import User
