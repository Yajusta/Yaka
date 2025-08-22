"""Modèle de données pour les libellés."""

from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING
import datetime

from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Mapped, mapped_column

from ..database import Base


class Label(Base):
    """Modèle de données pour les libellés."""

    __tablename__ = "labels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nom: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    couleur: Mapped[str] = mapped_column(String, nullable=False)  # Code hexadécimal
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relations
    creator: Mapped["User"] = relationship("User", back_populates="created_labels")
    cards: Mapped[List["Card"]] = relationship("Card", secondary="card_labels", back_populates="labels")


if TYPE_CHECKING:
    from .user import User
    from .card import Card
