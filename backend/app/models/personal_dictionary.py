"""Model for personal dictionary entries specific to each user."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .user import User


class PersonalDictionary(Base):
    """Model for personal dictionary entries managed by individual users."""

    __tablename__ = "personal_dictionary"
    __table_args__ = (UniqueConstraint("user_id", "term", name="uq_user_term"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    term: Mapped[str] = mapped_column(String(32), nullable=False)
    definition: Mapped[str] = mapped_column(String(250), nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="personal_dictionary_entries")

