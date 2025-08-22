"""Modèle de données pour les listes Kanban."""

from __future__ import annotations

from typing import List, Optional
import datetime

from sqlalchemy import Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Mapped, mapped_column

from ..database import Base


class KanbanList(Base):
    """Modèle de données pour les listes Kanban."""

    __tablename__ = "kanban_lists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    # Relations
    cards: Mapped[List["Card"]] = relationship("Card", back_populates="kanban_list")


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .card import Card