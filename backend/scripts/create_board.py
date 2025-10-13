#!/usr/bin/env python3
"""
Script to create a new database for a Yaka board.

Usage:
    python create_board.py <board_uid> [admin_email]

Example:
    python create_board.py client
    python create_board.py client admin@example.com
"""

import sys
import os
from typing import Optional
from app.multi_database import db_manager
from app.database import Base
from app.utils.validators import validate_email_format


def create_board_database(board_uid: str, admin_email: Optional[str] = None):
    """Create a complete database for a board."""
    print(f"Creating database for board: {board_uid}")

    # Validate board UID
    if not board_uid.replace("-", "").isalnum():
        print("ERROR: Board UID must contain only alphanumeric characters and hyphens")
        return False

    # Validate admin email if provided
    email_error = validate_email_format(admin_email)
    if email_error:
        print(f"ERROR: {email_error}")
        return False

    # Check if database already exists
    if db_manager.ensure_database_exists(board_uid):
        print(f"WARNING: Database '{board_uid}.db' already exists")
        return False

    # Create engine and tables
    try:
        # Create engine directly (bypass existence check)
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

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

        # Handle admin email logic if provided
        if admin_email:
            print(f"\nProcessing admin email: {admin_email}")

            # Create a session to handle database operations
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            db = SessionLocal()

            try:
                from app.models import User, UserRole
                from app.services import user as user_service

                # Send automatic invitation
                invited_user = user_service.invite_user(db, admin_email, None, UserRole.ADMIN, board_uid)
                print(f"✓ Invitation sent to {admin_email}")
                print(f"  Token: {invited_user.invite_token}")

                # Remove default admin "admin@yaka.local"
                default_admin = db.query(User).filter(
                    User.email == "admin@yaka.local"
                ).first()

                if default_admin:
                    db.delete(default_admin)
                    db.commit()
                    print(f"✓ Default admin 'admin@yaka.local' removed")

            except Exception as e:
                db.rollback()
                print(f"⚠ Warning: Database created but invitation failed: {e}")
            finally:
                db.close()

        return True

    except Exception as e:
        print(f"Error creating database: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python create_board.py <board_uid> [admin_email]")
        print("Example: python create_board.py client")
        print("Example: python create_board.py client admin@example.com")
        sys.exit(1)

    board_uid = sys.argv[1]
    admin_email = sys.argv[2] if len(sys.argv) == 3 else None

    success = create_board_database(board_uid, admin_email)
    sys.exit(0 if success else 1)
