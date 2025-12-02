"""Modèle de données pour les cartes."""

from __future__ import annotations

import datetime
import enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Column, Date, DateTime, Enum, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .helpers import get_system_timezone_datetime

if TYPE_CHECKING:
    from .card_comment import CardComment
    from .card_history import CardHistory
    from .card_item import CardItem
    from .kanban_list import KanbanList
    from .label import Label
    from .user import User


class CardPriority(enum.Enum):
    """Énumération des priorités de carte."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


card_labels = Table(
    "card_labels",
    Base.metadata,
    Column("card_id", Integer, ForeignKey("cards.id"), primary_key=True),
    Column("label_id", Integer, ForeignKey("labels.id"), primary_key=True),
)


class Card(Base):
    """Modèle de données pour les cartes."""

    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    due_date: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    priority: Mapped[CardPriority] = mapped_column(Enum(CardPriority), default=CardPriority.MEDIUM, nullable=False)
    list_id: Mapped[int] = mapped_column(Integer, ForeignKey("kanban_lists.id"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assignee_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), default=get_system_timezone_datetime
    )
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=get_system_timezone_datetime
    )

    # Relations
    kanban_list: Mapped["KanbanList"] = relationship("KanbanList", back_populates="cards")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by], back_populates="created_cards")
    assignee: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[assignee_id], back_populates="assigned_cards"
    )
    labels: Mapped[List["Label"]] = relationship("Label", secondary=card_labels, back_populates="cards")
    items: Mapped[List["CardItem"]] = relationship("CardItem", back_populates="card", cascade="all, delete-orphan")
    comments: Mapped[List["CardComment"]] = relationship(
        "CardComment", back_populates="card", cascade="all, delete-orphan"
    )
    history: Mapped[List["CardHistory"]] = relationship(
        "CardHistory", back_populates="card", cascade="all, delete-orphan"
    )

    PROTECTED_FIELDS: set[str] = {"id", "created_by", "created_at"}

    def __str__(self) -> str:
        """Représentation de la carte."""
        return f"<Card(id={self.id}, title='{self.title}')>"
