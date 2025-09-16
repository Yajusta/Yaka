"""Modèle de données pour les paramètres du tableau."""

import datetime
from typing import Optional

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ..database import Base
from .helpers import get_system_timezone_datetime


class BoardSettings(Base):
    """Modèle de données pour les paramètres du tableau Kanban."""

    __tablename__ = "board_settings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    setting_key: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    setting_value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=get_system_timezone_datetime
    )

    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=get_system_timezone_datetime
    )
