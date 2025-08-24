"""Modèle de données pour les utilisateurs."""

from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING
import enum
import datetime

from sqlalchemy import Integer, String, DateTime, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Mapped, mapped_column

from ..database import Base


class UserRole(enum.Enum):
    """Énumération des rôles utilisateur."""

    ADMIN = "admin"
    USER = "user"


class UserStatus(enum.Enum):
    """Énumération des statuts d'un utilisateur."""

    INVITED = "invited"
    ACTIVE = "active"
    DISABLED = "disabled"


class User(Base):
    """Modèle de données pour les utilisateurs."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER, nullable=False)
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False)
    invite_token: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    invited_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    # Relations
    # relationship() returns instrumented lists at runtime; to keep static
    # typing accurate without evaluating forward references at import time,
    # provide type-only annotations under TYPE_CHECKING and keep the runtime
    # assignments as plain relationship() calls.
    created_cards: Mapped[List["Card"]] = relationship(
        "Card", foreign_keys="Card.created_by", back_populates="creator"
    )
    assigned_cards: Mapped[List["Card"]] = relationship(
        "Card", foreign_keys="Card.assignee_id", back_populates="assignee"
    )
    created_labels: Mapped[List["Label"]] = relationship("Label", back_populates="creator")
    card_actions: Mapped[List["CardHistory"]] = relationship("CardHistory", back_populates="user")


if TYPE_CHECKING:
    from .card import Card
    from .label import Label
    from .card_history import CardHistory
