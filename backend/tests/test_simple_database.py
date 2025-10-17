"""Simple test to verify test database setup."""

import os
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base

# Import all models to register them with Base
from app.models.board_settings import BoardSettings
from app.models.card import Card
from app.models.card_comment import CardComment
from app.models.card_history import CardHistory
from app.models.card_item import CardItem
from app.models.global_dictionary import GlobalDictionary
from app.models.kanban_list import KanbanList
from app.models.label import Label
from app.models.personal_dictionary import PersonalDictionary
from app.models.user import User
from app.services.board_settings import initialize_default_settings
from app.services.user import create_admin_user, get_user_by_email


def test_simple_database_setup():
    """Test simple database setup without FastAPI."""
    # Setup database
    test_db_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(test_db_dir, exist_ok=True)
    test_db_path = os.path.join(test_db_dir, "test_simple_yaka.db")
    
    # Remove existing test db if it exists
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    
    database_url = f"sqlite:///{test_db_path}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    db = SessionLocal()
    
    try:
        # Create admin user
        admin_user = get_user_by_email(db, "admin@yaka.local")
        if not admin_user:
            create_admin_user(db)
        
        # Initialize settings
        initialize_default_settings(db)
        
        # Verify user exists
        admin_user = get_user_by_email(db, "admin@yaka.local")
        assert admin_user is not None
        assert admin_user.email == "admin@yaka.local"
        
        print("✓ Test database setup works correctly")
        
    finally:
        db.close()
        # Dispose of the engine to release the file lock
        engine.dispose()
    
    # Clean up
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


if __name__ == "__main__":
    test_simple_database_setup()