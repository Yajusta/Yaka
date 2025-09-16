"""Modèle de données pour les listes Kanban."""

from __future__ import annotations

import datetime
from typing import List, Optional

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..database import Base
from .helpers import get_system_timezone_datetime


class KanbanList(Base):
    """Modèle de données pour les listes Kanban."""

    __tablename__ = "kanban_lists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=get_system_timezone_datetime
    )
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=get_system_timezone_datetime
    )

    # Relations
    cards: Mapped[List["Card"]] = relationship("Card", back_populates="kanban_list")


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .card import Card
