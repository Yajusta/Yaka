"""Modèle de données pour les commentaires d'une carte."""

from __future__ import annotations

from typing import Optional
import datetime

from sqlalchemy import Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column

from ..database import Base


def get_system_timezone_datetime():
    """Retourne la date et heure actuelle dans le fuseau horaire du système."""
    return datetime.datetime.now().astimezone()


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


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .card import Card
    from .user import User
