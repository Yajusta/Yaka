"""Modèle de données pour les utilisateurs."""

from __future__ import annotations

import datetime
import enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, Enum, Index, Integer, String, false, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .helpers import get_system_timezone_datetime


class UserRole(enum.Enum):
    """User role enumeration.

    Hierarchical structure:
    - VISITOR: Read-only access (board, tasks, comments)
    - COMMENTER: VISITOR + add/edit own comments
    - CONTRIBUTOR: COMMENTER + self-assign + checklist items + move own tasks
    - EDITOR: CONTRIBUTOR + create task + fully modify own tasks
    - SUPERVISOR: EDITOR + create task for others + modify all tasks + move all tasks
    - ADMIN: SUPERVISOR + full access + manage users/settings
    """

    VISITOR = "visitor"
    COMMENTER = "commenter"
    CONTRIBUTOR = "contributor"
    EDITOR = "editor"
    SUPERVISOR = "supervisor"
    ADMIN = "admin"


class UserStatus(enum.Enum):
    """User status enumeration."""

    INVITED = "invited"
    ACTIVE = "active"
    # DISABLED = "disabled"
    DELETED = "deleted"


class ViewScope(enum.Enum):
    """View scope enumeration for card access permissions."""

    ALL = "all"  # User can see all cards
    UNASSIGNED_PLUS_MINE = (
        "unassigned_plus_mine"  # User can see unassigned cards + their assigned cards
    )
    MINE_ONLY = "mine_only"  # User can only see their assigned cards


class User(Base):
    """User data model."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, index=True, nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            native_enum=False,
            values_callable=lambda obj: [e.value for e in obj],
            length=20,
        ),
        default=UserRole.VISITOR,
        nullable=False,
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(
            UserStatus,
            native_enum=False,
            values_callable=lambda obj: [e.value for e in obj],
            length=20,
        ),
        default=UserStatus.ACTIVE,
        nullable=False,
    )
    language: Mapped[Optional[str]] = mapped_column(
        String(2), nullable=True, server_default="fr"
    )
    view_scope: Mapped[ViewScope] = mapped_column(
        Enum(
            ViewScope,
            native_enum=False,
            values_callable=lambda obj: [e.value for e in obj],
            length=25,
        ),
        default=ViewScope.ALL,
        nullable=False,
    )
    invite_token: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, index=True
    )
    invited_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Changement de mot de passe exigé avant tout autre accès (admin initial aléatoire)
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    # Version des jetons de session : tout JWT portant une autre version est
    # refusé (incrémentée au changement de mot de passe, rôle, statut, déconnexion)
    token_version: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
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
            sqlite_where=text("lower(status) != 'deleted'"),
            postgresql_where=text("lower(status) != 'deleted'"),
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
    created_labels: Mapped[List["Label"]] = relationship(
        "Label", back_populates="creator"
    )
    card_comments: Mapped[List["CardComment"]] = relationship(
        "CardComment", back_populates="user"
    )
    card_actions: Mapped[List["CardHistory"]] = relationship(
        "CardHistory", back_populates="user"
    )
    personal_dictionary_entries: Mapped[List["PersonalDictionary"]] = relationship(
        "PersonalDictionary", back_populates="user"
    )

    PROTECTED_FIELDS = {"id", "created_at"}


if TYPE_CHECKING:
    from .card import Card
    from .card_comment import CardComment
    from .card_history import CardHistory
    from .label import Label
    from .personal_dictionary import PersonalDictionary
