"""Simple test to verify test database setup."""

import pytest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.test_database import setup_test_database, SessionLocal, Base

# Import all models to register them with the test Base
from app.models.user import User
from app.models.board_settings import BoardSettings
from app.models.kanban_list import KanbanList
from app.models.label import Label
from app.models.card import Card
from app.models.card_comment import CardComment
from app.models.card_history import CardHistory
from app.models.card_item import CardItem

from app.services.user import create_admin_user, get_user_by_email
from app.services.board_settings import initialize_default_settings


def test_simple_database_setup():
    """Test simple database setup without FastAPI."""
    # Setup database
    engine = setup_test_database()
    
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
    
    # Clean up
    if os.path.exists("data/test_yaka.db"):
        os.remove("data/test_yaka.db")


if __name__ == "__main__":
    test_simple_database_setup()