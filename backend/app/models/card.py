"""Modèle de données pour les cartes."""

from __future__ import annotations

from typing import List, Optional
import enum
import datetime

from sqlalchemy import Integer, String, Text, Date, DateTime, Boolean, ForeignKey, Enum, Table
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Mapped, mapped_column

from ..database import Base


class CardStatus(enum.Enum):
    """Énumération des statuts de carte."""

    A_FAIRE = "a_faire"
    EN_COURS = "en_cours"
    TERMINE = "termine"


class CardPriority(enum.Enum):
    """Énumération des priorités de carte."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Table d'association pour la relation many-to-many entre Card et Label
from sqlalchemy import Column

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
    titre: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    date_echeance: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    priorite: Mapped[CardPriority] = mapped_column(Enum(CardPriority), default=CardPriority.MEDIUM, nullable=False)
    list_id: Mapped[int] = mapped_column(Integer, ForeignKey("kanban_lists.id"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assignee_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    # Relations
    kanban_list: Mapped["KanbanList"] = relationship("KanbanList", back_populates="cards")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by], back_populates="created_cards")
    assignee: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[assignee_id], back_populates="assigned_cards"
    )
    labels: Mapped[List["Label"]] = relationship("Label", secondary=card_labels, back_populates="cards")
    items: Mapped[List["CardItem"]] = relationship("CardItem", back_populates="card", cascade="all, delete-orphan")
    comments: Mapped[List["CardComment"]] = relationship("CardComment", back_populates="card", cascade="all, delete-orphan")
    history: Mapped[List["CardHistory"]] = relationship("CardHistory", back_populates="card", cascade="all, delete-orphan")


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .user import User
    from .label import Label
    from .kanban_list import KanbanList
    from .card_item import CardItem
    from .card_comment import CardComment
    from .card_history import CardHistory
