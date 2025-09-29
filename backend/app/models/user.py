"""Modèle de données pour les utilisateurs."""

from __future__ import annotations

import datetime
import enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, Enum, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..database import Base
from .helpers import get_system_timezone_datetime


class UserRole(enum.Enum):
    """Énumération des rôles utilisateur."""

    ADMIN = "admin"
    USER = "user"
    READ_ONLY = "read_only"
    COMMENTS_ONLY = "comments_only"
    ASSIGNED_ONLY = "assigned_only"


class UserStatus(enum.Enum):
    """Énumération des statuts d'un utilisateur."""

    INVITED = "invited"
    ACTIVE = "active"
    # DISABLED = "disabled"
    DELETED = "deleted"


class User(Base):
    """Modèle de données pour les utilisateurs."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, index=True, nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER, nullable=False)
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False)
    language: Mapped[Optional[str]] = mapped_column(String(2), nullable=True, server_default="fr")
    invite_token: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    invited_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), default=get_system_timezone_datetime
    )
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=get_system_timezone_datetime
    )

    __table_args__ = (
        Index(
            "ux_users_email_not_deleted",
            "email",
            unique=True,
            sqlite_where=text("status != 'DELETED'"),
            postgresql_where=text("status != 'DELETED'"),
        ),
    )

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
    card_comments: Mapped[List["CardComment"]] = relationship("CardComment", back_populates="user")
    card_actions: Mapped[List["CardHistory"]] = relationship("CardHistory", back_populates="user")

    PROTECTED_FIELDS = {"id", "created_at"}


if TYPE_CHECKING:
    from .card import Card
    from .card_comment import CardComment
    from .card_history import CardHistory
    from .label import Label
