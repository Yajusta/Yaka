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
from typing import Callable, List, Optional, Tuple

from app.database import Base
from app.multi_database import (
    DEFAULT_BOARD_UID,
    db_manager,
    is_valid_board_uid,
    publish_board_database,
)
from app.utils.validators import validate_email_format


def _build_board(
    build_path: str, board_uid: str, admin_email: Optional[str]
) -> List[Tuple[Callable[..., None], tuple, dict]]:
    """Create the complete board database at `build_path`.

    Returns the invitation emails to send once the board is published: sent
    earlier, they would carry a token for a board whose publication may fail.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    pending_emails: List[Tuple[Callable[..., None], tuple, dict]] = []
    engine = create_engine(
        f"sqlite:///{build_path}", connect_args={"check_same_thread": False}
    )
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print(f"Tables created successfully for board {board_uid}")

        # Initialize alembic_version table
        db_manager._initialize_alembic_version(engine)
        print("Alembic version initialized")

        # Handle admin email logic if provided
        if admin_email:
            print(f"\nProcessing admin email: {admin_email}")

            # Create a session to handle database operations
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            db = SessionLocal()

            try:
                from app.models import UserRole
                from app.services import user as user_service
                from app.services.board_settings import initialize_default_settings
                from app.utils.demo_reset import create_demo_board_content

                # Initialize board settings
                print("Initializing board settings...")
                initialize_default_settings(db)
                print("Board settings initialized")

                # Send automatic invitation (this creates the admin user)
                invited_user = user_service.invite_user(
                    db,
                    admin_email,
                    None,
                    UserRole.ADMIN,
                    board_uid,
                    defer=lambda func, *args, **kwargs: pending_emails.append(
                        (func, args, kwargs)
                    ),
                )
                print(f"Invitation created for {admin_email}")
                print(f"  Token: {invited_user.invite_token}")

                # Create demo board content with the invited admin user
                print("Creating demo board content...")
                create_demo_board_content(db, admin_user=invited_user)
                print("Demo board content created (lists, labels, and initial task)")

            except Exception as e:
                db.rollback()
                print(f"⚠ Warning: Database created but invitation failed: {e}")
            finally:
                db.close()
    finally:
        # Release the file before it is published
        engine.dispose()
    return pending_emails


def create_board_database(board_uid: str, admin_email: Optional[str] = None):
    """Create a complete database for a board."""
    print(f"Creating database for board: {board_uid}")

    # Same rule as the middleware and the admin routes
    if not is_valid_board_uid(board_uid):
        print(
            "ERROR: Board UID must contain only alphanumeric characters and hyphens, "
            "with length between 1 and 50"
        )
        return False

    # Any case of the default board's name is reserved (see admin create_board)
    if board_uid.lower() == DEFAULT_BOARD_UID:
        print(f"WARNING: Board '{board_uid}' is reserved for the default database")
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

    try:
        # Built in a temporary file, published only once complete
        pending_emails = publish_board_database(
            board_uid,
            lambda build_path: _build_board(build_path, board_uid, admin_email),
        )
    except FileExistsError:
        print(f"WARNING: Database '{board_uid}.db' already exists")
        return False
    except Exception as e:
        print(f"Error creating database: {e}")
        return False

    for func, args, kwargs in pending_emails:
        func(*args, **kwargs)
    if pending_emails:
        print(f"Invitation sent to {admin_email}")

    print(f"Database '{board_uid}.db' created successfully!")
    print(f"   Path: ./data/{board_uid}.db")
    print(f"   Access: /board/{board_uid}/")
    return True


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
