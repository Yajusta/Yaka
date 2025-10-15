"""Administrative routes for board management."""

import os
from fastapi import APIRouter, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List

from ..multi_database import db_manager
from ..database import Base
from ..utils.validators import validate_email_format
from sqlalchemy import create_engine

router = APIRouter(prefix="/admin", tags=["admin"])
security = HTTPBearer()


class CreateBoardRequest(BaseModel):
    board_uid: str
    admin_email: str | None = None


class BoardInfo(BaseModel):
    board_uid: str
    exists: bool
    path: str


def verify_admin_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify the admin API key for secure operations."""
    # Read API key at runtime instead of module load time to support testing
    admin_api_key = os.getenv("YAKA_ADMIN_API_KEY")

    if not admin_api_key:
        raise HTTPException(status_code=503, detail="Board creation service is not configured")

    if credentials.credentials != admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing admin API key")

    return True


@router.post("/boards", status_code=201)
async def create_board(request: CreateBoardRequest, authorized: bool = Depends(verify_admin_api_key)):
    """
    Create a new database for a board.

    This administrative endpoint allows manual board creation.
    Requires a valid admin API key.
    """
    board_uid = request.board_uid
    admin_email = request.admin_email

    # Validate board UID (alphanumeric and hyphens only, 1-50 characters)
    import re

    if not re.match(r"^[a-zA-Z0-9-]{1,50}$", board_uid):
        raise HTTPException(
            status_code=400,
            detail="Board UID must contain only alphanumeric characters and hyphens, with length between 1 and 50",
        )

    # Validate admin email if provided
    email_error = validate_email_format(admin_email)
    if email_error:
        raise HTTPException(
            status_code=400,
            detail=email_error,
        )

    # Check if board already exists
    if db_manager.ensure_database_exists(board_uid):
        raise HTTPException(status_code=409, detail=f"Board '{board_uid}' already exists")

    try:
        # Create engine directly
        db_path = db_manager.get_database_path(board_uid)
        engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

        try:
            # Create all tables
            Base.metadata.create_all(bind=engine)

            # Initialize alembic_version
            db_manager._initialize_alembic_version(engine)

            result = {
                "message": f"Board '{board_uid}' created successfully",
                "board_uid": board_uid,
                "database_path": db_path,
                "access_url": f"/board/{board_uid}/",
            }

            # Handle admin email logic if provided
            if admin_email:
                from ..models import User, UserRole
                from ..services import user as user_service

                # Create a session to handle database operations
                from sqlalchemy.orm import sessionmaker
                SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
                db = SessionLocal()

                try:
                    # Initialize default board data (lists, labels, and initial task)
                    from ..utils.demo_reset import initialize_default_data, create_demo_data

                    # Create default admin user and settings
                    initialize_default_data(db)

                    # Create demo data (lists, labels, and initial configuration task)
                    create_demo_data(db)

                    # Send automatic invitation
                    invited_user = user_service.invite_user(db, admin_email, None, UserRole.ADMIN, board_uid)
                    result["invitation_sent"] = str(True)
                    result["invited_email"] = admin_email
                    result["invitation_token"] = str(invited_user.invite_token)

                    # Remove default admin "admin@yaka.local"
                    default_admin = db.query(User).filter(
                        User.email == "admin@yaka.local"
                    ).first()

                    if default_admin:
                        db.delete(default_admin)
                        db.commit()
                        result["default_admin_removed"] = str(True)

                    result["default_data_initialized"] = str(True)

                except Exception as e:
                    db.rollback()
                    # Log the error but don't fail the board creation
                    result["invitation_warning"] = f"Board created but invitation failed: {str(e)}"
                finally:
                    db.close()

            return result
        finally:
            # Always dispose the engine to release the database lock
            engine.dispose()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating board: {str(e)}")


@router.get("/boards")
async def list_boards(authorized: bool = Depends(verify_admin_api_key)):
    """List all existing boards."""
    import os

    data_dir = db_manager.base_path
    if not os.path.exists(data_dir):
        return {"boards": []}

    boards = []
    for file in os.listdir(data_dir):
        if file.endswith(".db"):
            board_uid = file[:-3]  # Remove .db
            if board_uid != "yaka":  # Exclude default database
                boards.append(
                    {
                        "board_uid": board_uid,
                        "database_path": f"{data_dir}/{file}",
                        "access_url": f"/board/{board_uid}/",
                    }
                )

    return {"boards": sorted(boards, key=lambda x: x["board_uid"])}


@router.get("/boards/{board_uid}")
async def get_board_info(board_uid: str):
    """Get information about a specific board."""
    exists = db_manager.ensure_database_exists(board_uid)

    return {
        "board_uid": board_uid,
        "exists": exists,
        "database_path": db_manager.get_database_path(board_uid) if exists else None,
        "access_url": f"/board/{board_uid}/" if exists else None,
    }


@router.delete("/boards/{board_uid}")
async def delete_board(board_uid: str, authorized: bool = Depends(verify_admin_api_key)):
    """
    Archive a board by moving its database to the deleted folder.
    The database file is renamed with a timestamp for safe keeping.
    Requires a valid admin API key.
    """
    if board_uid == "yaka":
        raise HTTPException(status_code=403, detail="Cannot delete default board 'yaka'")

    if not db_manager.ensure_database_exists(board_uid):
        raise HTTPException(status_code=404, detail=f"Board '{board_uid}' does not exist")

    try:
        import os
        from datetime import datetime
        import shutil

        # Get original database path
        original_path = db_manager.get_database_path(board_uid)

        # Create deleted directory if it doesn't exist
        deleted_dir = os.path.join(db_manager.base_path, "deleted")
        os.makedirs(deleted_dir, exist_ok=True)
        

        # Generate timestamp for unique filename
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        deleted_filename = f"{board_uid}.{timestamp}.db"
        deleted_path = os.path.join(deleted_dir, deleted_filename)

        # Move the database file
        shutil.move(original_path, deleted_path)

        return {
            "message": f"Board '{board_uid}' archived successfully",
            "original_path": original_path,
            "archived_path": deleted_path,
            "archived_at": datetime.now().isoformat(),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error archiving board: {str(e)}")
