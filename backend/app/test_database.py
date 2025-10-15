"""SQLite test database configuration."""

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .database import Base

# SQLite database file used for tests
TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "tests", "data", "test_yaka.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"

# Dedicated SQLAlchemy engine for tests
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

# Session factory bound to the test engine
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_test_db() -> Generator:
    """Yield a database session bound to the test engine."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def setup_test_database():
    """Create a fresh SQLite database populated with the application models."""
    os.makedirs(os.path.dirname(TEST_DB_PATH), exist_ok=True)

    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    # Import models so they are registered on the shared metadata before create_all.
    from app.models.user import User  # noqa: F401
    from app.models.board_settings import BoardSettings  # noqa: F401
    from app.models.kanban_list import KanbanList  # noqa: F401
    from app.models.label import Label  # noqa: F401
    from app.models.card import Card  # noqa: F401
    from app.models.card_comment import CardComment  # noqa: F401
    from app.models.card_history import CardHistory  # noqa: F401
    from app.models.card_item import CardItem  # noqa: F401

    Base.metadata.create_all(bind=engine)

    return engine


def teardown_test_database():
    """Remove the SQLite file backing the test database."""
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


def clean_test_database():
    """Delete data from the test database while keeping the schema."""
    db = SessionLocal()
    try:
        try:
            from app.models.card_item import CardItem
            from app.models.card_comment import CardComment
            from app.models.card_history import CardHistory
            from app.models.card import Card
            from app.models.label import Label
            from app.models.kanban_list import KanbanList
            from app.models.board_settings import BoardSettings
            from app.models.user import User

            db.query(CardItem).delete()
            db.query(CardComment).delete()
            db.query(CardHistory).delete()

            try:
                db.execute("DELETE FROM card_labels")
            except Exception:
                pass

            db.query(Card).delete()
            db.query(Label).delete()
            db.query(KanbanList).delete()
            db.query(BoardSettings).delete()
            db.query(User).delete()

            db.commit()
        except Exception:
            pass
    except Exception as exc:
        db.rollback()
        raise exc
    finally:
        db.close()
