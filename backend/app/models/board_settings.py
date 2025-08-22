"""Modèle de données pour les paramètres du tableau."""

from typing import Optional
import datetime
from sqlalchemy import String, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base


class BoardSettings(Base):
    """Modèle de données pour les paramètres du tableau Kanban."""

    __tablename__ = "board_settings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    setting_key: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    setting_value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())