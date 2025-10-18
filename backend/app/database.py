"""Configuration de la base de données SQLite."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import sessionmaker
from typing import Generator

# Default database URL
SQLALCHEMY_DATABASE_URL = "sqlite:///./data/yaka.db"

# Default engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30},
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Default session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Base for models (SQLAlchemy 2.0 DeclarativeBase for typed mappings)
class Base(DeclarativeBase):
    pass


def get_db() -> Generator:
    """
    Generator for database session (default).

    For requests with board context, use get_dynamic_db()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Import dynamic functions for easy access
try:
    from .multi_database import get_dynamic_db, get_board_db, set_current_board_uid, get_current_board_uid

    __all__ = [
        "Base",
        "engine",
        "SessionLocal",
        "get_db",  # Default functions
        "get_dynamic_db",
        "get_board_db",
        "set_current_board_uid",
        "get_current_board_uid",  # Dynamic functions
    ]
except ImportError:
    # In case of circular import, provide only the base functions
    __all__ = ["Base", "engine", "SessionLocal", "get_db"]
