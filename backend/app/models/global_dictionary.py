"""Model for global dictionary entries accessible to all users."""

from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class GlobalDictionary(Base):
    """Model for global dictionary entries managed by administrators."""

    __tablename__ = "global_dictionary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    term: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    definition: Mapped[str] = mapped_column(String(250), nullable=False)
