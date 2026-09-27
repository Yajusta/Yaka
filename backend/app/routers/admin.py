"""Administrative routes for board management."""

import hmac
import logging
import os

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import create_engine

from ..database import Base
from ..multi_database import (
    DEFAULT_BOARD_UID,
    db_manager,
    evict_board,
    is_valid_board_uid,
    publish_board_database,
)
from ..utils.validators import validate_email_format

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])
security = HTTPBearer()

ADMIN_API_KEY_MIN_LENGTH = 32


class CreateBoardRequest(BaseModel):
    board_uid: str
    admin_email: str | None = None


class BoardInfo(BaseModel):
    board_uid: str
    exists: bool
    path: str


def verify_admin_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security),
):
    """Verify the admin API key for secure operations."""
    # Read API key at runtime instead of module load time to support testing
    admin_api_key = os.getenv("YAKA_ADMIN_API_KEY")

    # A missing or weak key (including the old .env.sample placeholder, which is
    # shorter than the minimum) is treated as "not configured"
    if not admin_api_key or len(admin_api_key) < ADMIN_API_KEY_MIN_LENGTH:
        if admin_api_key:
            # Explain the 503 to the operator: the key is set but rejected
            logger.warning(
                "YAKA_ADMIN_API_KEY is set but shorter than %d characters: "
                "/admin endpoints are disabled (generate one with: openssl rand -hex 32)",
                ADMIN_API_KEY_MIN_LENGTH,
            )
        raise HTTPException(
            status_code=503, detail="Board creation service is not configured"
        )

    # Constant-time comparison
    if not hmac.compare_digest(
        credentials.credentials.encode("utf-8"), admin_api_key.encode("utf-8")
    ):
        raise HTTPException(status_code=401, detail="Invalid or missing admin API key")

    return True


def _validate_board_uid(board_uid: str) -> None:
    """Reject board UIDs that could not be served (same rule as the middleware)."""
    if not is_valid_board_uid(board_uid):
        raise HTTPException(
            status_code=400,
            detail="Board UID must contain only alphanumeric characters and hyphens, with length between 1 and 50",
        )


# Blocking file and database work: plain `def` runs in the threadpool
@router.post("/boards", status_code=201)
def create_board(
    request: CreateBoardRequest,
    background_tasks: BackgroundTasks,
    authorized: bool = Depends(verify_admin_api_key),
):
    """
    Create a new database for a board.

    This administrative endpoint allows manual board creation.
    Requires a valid admin API key.
    """
    board_uid = request.board_uid
    admin_email = request.admin_email

    _validate_board_uid(board_uid)

    # Validate admin email if provided
    email_error = validate_email_format(admin_email)
    if email_error:
        raise HTTPException(
            status_code=400,
            detail=email_error,
        )

    # Any case of the default board's name is reserved: it could never be
    # deleted (see delete_board) and is the default database on Windows/macOS.
    # The existence check only saves the build work; the atomic publish in
    # publish_board_database settles concurrent creations.
    if board_uid.lower() == DEFAULT_BOARD_UID or db_manager.ensure_database_exists(
        board_uid
    ):
        raise HTTPException(
            status_code=409, detail=f"Board '{board_uid}' already exists"
        )

    db_path = db_manager.get_database_path(board_uid)
    try:
        # Built in a temporary file, published only once complete
        return publish_board_database(
            board_uid,
            lambda build_path: _build_board(
                build_path, board_uid, db_path, admin_email, background_tasks
            ),
        )
    except FileExistsError:
        raise HTTPException(
            status_code=409, detail=f"Board '{board_uid}' already exists"
        ) from None
    except Exception as e:
        logger.exception("Error creating board %s", board_uid)
        raise HTTPException(status_code=500, detail="Error creating board") from e


def _build_board(
    build_path: str,
    board_uid: str,
    db_path: str,
    admin_email: str | None,
    background_tasks: BackgroundTasks,
) -> dict:
    """Create the complete board database at `build_path` (see create_board)."""
    engine = create_engine(
        f"sqlite:///{build_path}", connect_args={"check_same_thread": False}
    )
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
            # Create a session to handle database operations
            from sqlalchemy.orm import sessionmaker

            from ..models import UserRole
            from ..services import user as user_service

            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            db = SessionLocal()

            try:
                # Initialize default board data (lists, labels, and initial task)
                from ..services.board_settings import initialize_default_settings
                from ..utils.demo_reset import create_demo_board_content

                # Initialize board settings
                initialize_default_settings(db)

                # Send automatic invitation (this creates the admin user);
                # the email goes out after the response (no SMTP on the event loop)
                invited_user = user_service.invite_user(
                    db,
                    admin_email,
                    None,
                    UserRole.ADMIN,
                    board_uid,
                    defer=background_tasks.add_task,
                )
                result["invitation_sent"] = str(True)
                result["invited_email"] = admin_email
                result["invitation_token"] = str(invited_user.invite_token)

                # Create demo board content (lists, labels, and initial configuration task) with the invited admin user.
                # The admin user is already committed and its email queued: a failure here
                # is reported separately, not as an invitation failure.
                try:
                    create_demo_board_content(db, admin_user=invited_user)
                    result["default_data_initialized"] = str(True)
                except Exception:
                    db.rollback()
                    logger.exception(
                        "Default data initialization failed for board %s",
                        board_uid,
                    )
                    result["default_data_warning"] = (
                        "Board created but default data failed"
                    )

            except Exception:
                db.rollback()
                # Log the error but don't fail the board creation
                logger.exception("Invitation failed for board %s", board_uid)
                result["invitation_warning"] = "Board created but invitation failed"
            finally:
                db.close()

        return result
    finally:
        # Always dispose the engine to release the database lock
        engine.dispose()


@router.get("/boards")
def list_boards(authorized: bool = Depends(verify_admin_api_key)):
    """List all existing boards."""
    data_dir = db_manager.base_path
    if not os.path.exists(data_dir):
        return {"boards": []}

    boards = []
    for file in os.listdir(data_dir):
        if file.endswith(".db"):
            board_uid = file[:-3]  # Remove .db
            if board_uid != DEFAULT_BOARD_UID:  # Exclude default database
                boards.append(
                    {
                        "board_uid": board_uid,
                        "database_path": f"{data_dir}/{file}",
                        "access_url": f"/board/{board_uid}/",
                    }
                )

    return {"boards": sorted(boards, key=lambda x: x["board_uid"])}


@router.get("/boards/{board_uid}")
def get_board_info(board_uid: str, authorized: bool = Depends(verify_admin_api_key)):
    """Get information about a specific board. Requires a valid admin API key."""
    _validate_board_uid(board_uid)
    exists = db_manager.ensure_database_exists(board_uid)

    return {
        "board_uid": board_uid,
        "exists": exists,
        "access_url": f"/board/{board_uid}/" if exists else None,
    }


@router.delete("/boards/{board_uid}")
def delete_board(board_uid: str, authorized: bool = Depends(verify_admin_api_key)):
    """
    Archive a board by moving its database to the deleted folder.
    The database file is renamed with a timestamp for safe keeping.
    Requires a valid admin API key.
    """
    _validate_board_uid(board_uid)

    # Case-insensitive: "Yaka" is the default database on Windows/macOS
    if board_uid.lower() == DEFAULT_BOARD_UID:
        raise HTTPException(
            status_code=403,
            detail=f"Cannot delete default board '{DEFAULT_BOARD_UID}'",
        )

    if not db_manager.ensure_database_exists(board_uid):
        raise HTTPException(
            status_code=404, detail=f"Board '{board_uid}' does not exist"
        )

    try:
        from datetime import datetime

        # Get original database path
        original_path = db_manager.get_database_path(board_uid)

        # Create deleted directory if it doesn't exist
        deleted_dir = os.path.join(db_manager.base_path, "deleted")
        os.makedirs(deleted_dir, exist_ok=True)

        # Generate timestamp for unique filename. Microseconds: os.rename
        # silently replaces an existing archive on POSIX (and fails on
        # Windows) when a board is recreated and deleted within one second
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S_%f")
        deleted_filename = f"{board_uid}.{timestamp}.db"
        deleted_path = os.path.join(deleted_dir, deleted_filename)

        # Release the cached engine (open file handles) before moving the file
        evict_board(board_uid)
        try:
            # Same filesystem (deleted/ is inside the data directory): a plain
            # rename either succeeds or fails whole, whereas shutil.move falls
            # back to copy + unlink and leaves a stray archive copy when the
            # unlink fails (file still open on Windows)
            os.rename(original_path, deleted_path)
        finally:
            # Drop any engine a concurrent request cached in the meantime
            evict_board(board_uid)

        return {
            "message": f"Board '{board_uid}' archived successfully",
            "original_path": original_path,
            "archived_path": deleted_path,
            "archived_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.exception("Error archiving board %s", board_uid)
        raise HTTPException(status_code=500, detail="Error archiving board") from e
