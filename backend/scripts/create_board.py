#!/usr/bin/env python3
"""
Script to create a new database for a Yaka board.

Usage:
    python create_board.py <board_uid>

Example:
    python create_board.py client
"""

import sys
import os
from app.multi_database import db_manager
from app.database import Base


def create_board_database(board_uid: str):
    """Create a complete database for a board."""
    print(f"Creating database for board: {board_uid}")

    # Validate board UID
    if not board_uid.replace("-", "").isalnum():
        print("ERROR: Board UID must contain only alphanumeric characters and hyphens")
        return False

    # Check if database already exists
    if db_manager.ensure_database_exists(board_uid):
        print(f"WARNING: Database '{board_uid}.db' already exists")
        return False

    # Create engine and tables
    try:
        # Create engine directly (bypass existence check)
        from sqlalchemy import create_engine

        db_path = db_manager.get_database_path(board_uid)
        engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

        # Create all tables
        Base.metadata.create_all(bind=engine)
        print(f"Tables created successfully in {board_uid}.db")

        # Initialize alembic_version table
        db_manager._initialize_alembic_version(engine)
        print(f"Alembic version initialized")

        print(f"Database '{board_uid}.db' created successfully!")
        print(f"   Path: ./data/{board_uid}.db")
        print(f"   Access: /board/{board_uid}/")

        return True

    except Exception as e:
        print(f"Error creating database: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python create_board.py <board_uid>")
        print("Example: python create_board.py client")
        sys.exit(1)

    board_uid = sys.argv[1]
    success = create_board_database(board_uid)
    sys.exit(0 if success else 1)
