"""Modèle de données pour les libellés."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .helpers import get_system_timezone_datetime


class Label(Base):
    """Modèle de données pour les libellés."""

    __tablename__ = "labels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    color: Mapped[str] = mapped_column(String, nullable=False)  # Code hexadécimal
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), default=get_system_timezone_datetime
    )

    # Relations
    creator: Mapped["User"] = relationship("User", back_populates="created_labels")
    cards: Mapped[List["Card"]] = relationship("Card", secondary="card_labels", back_populates="labels")


if TYPE_CHECKING:
    from .card import Card
    from .user import User
