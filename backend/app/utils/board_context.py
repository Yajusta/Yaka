"""Middleware for extracting board UID from URLs."""

import re
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ..multi_database import is_valid_board_uid, set_current_board_uid

# Paths of the form /board/{board_uid}/...
_BOARD_PATH_PATTERN = re.compile(r"^/board/([^/]+)/")


class BoardContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware that extracts board_uid from URLs in the form /board/{board_uid}/... and makes it available in the request context
    for services to use the correct database.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Reset context at the beginning of each request
        set_current_board_uid(None)

        # Extract board_uid from the request path
        path = request.url.path

        board_match = _BOARD_PATH_PATTERN.match(path)

        if board_match:
            board_uid = board_match.group(1)
            # An invalid uid is rejected like a missing board: ignoring it
            # would serve the route against the default database
            if not self._is_valid_board_uid(
                board_uid
            ) or not self._board_database_exists(board_uid):
                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": f"Board '{board_uid}' not found or access denied"
                    },
                )

            set_current_board_uid(board_uid)
            # Also store in request.state for direct access if needed
            request.state.board_uid = board_uid

        try:
            # Continue processing the request
            response = await call_next(request)
            return response
        except ValueError as e:
            # Intercept board not found errors from multi-database manager
            if "not found" in str(e):
                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": str(e).replace(
                            "not found", "not found or access denied"
                        )
                    },
                )
            raise
        finally:
            # Clean up context at the end of the request
            set_current_board_uid(None)

    def _board_database_exists(self, board_uid: str) -> bool:
        """
        Check that the database exists for a board.

        Args:
            board_uid: The board identifier to check

        Returns:
            True if the database exists, False otherwise
        """
        from ..multi_database import db_manager

        return db_manager.ensure_database_exists(board_uid)

    # Single rule shared with the admin routes (multi_database)
    _is_valid_board_uid = staticmethod(is_valid_board_uid)


def get_board_uid_from_request(request: Request) -> str | None:
    """
    Utility function to extract board_uid from a request.

    Args:
        request: The FastAPI request

    Returns:
        The board_uid if present, None otherwise
    """
    # Try to get it from request.state first
    if hasattr(request.state, "board_uid"):
        return request.state.board_uid

    # Otherwise, try to extract from the path
    path = request.url.path
    board_match = _BOARD_PATH_PATTERN.match(path)

    if board_match:
        board_uid = board_match.group(1)
        if is_valid_board_uid(board_uid):
            return board_uid

    return None
