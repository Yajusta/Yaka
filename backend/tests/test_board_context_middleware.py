"""Tests for the board context middleware."""

import os
import tempfile
from unittest.mock import MagicMock

import pytest
from app.database import Base
from app.multi_database import db_manager, get_current_board_uid, set_current_board_uid
from app.utils.board_context import BoardContextMiddleware, get_board_uid_from_request
from fastapi import Request
from sqlalchemy import create_engine


class TestBoardContextMiddleware:
    """Test cases for the BoardContextMiddleware."""

    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary directory for test databases."""
        with tempfile.TemporaryDirectory() as temp_dir:
            old_base_path = db_manager.base_path
            db_manager.base_path = temp_dir
            yield temp_dir
            db_manager.base_path = old_base_path

    @pytest.fixture
    def create_test_database(self, temp_data_dir):
        """Factory function to create test databases."""

        def _create(board_uid: str):
            db_path = os.path.join(temp_data_dir, f"{board_uid}.db")
            engine = create_engine(f"sqlite:///{db_path}")
            Base.metadata.create_all(bind=engine)
            return db_path

        return _create

    @pytest.fixture
    def middleware(self):
        """Create a BoardContextMiddleware instance."""
        # Create a mock ASGI app for the middleware
        mock_app = MagicMock()
        middleware = BoardContextMiddleware(mock_app)
        yield middleware

    def create_mock_request(self, path: str) -> Request:
        """Create a mock FastAPI Request object."""
        mock_request = MagicMock()
        mock_request.url = MagicMock()
        mock_request.url.path = path

        # Create a simple object for state instead of MagicMock
        class SimpleState:
            pass

        mock_request.state = SimpleState()
        return mock_request

    def create_mock_call_next(self, check_context=True):
        """Create a mock call_next function."""

        async def mock_call_next(request):
            # Check that board UID is set during request processing (if requested)
            if check_context:
                if hasattr(request.state, "board_uid"):
                    assert get_current_board_uid() == request.state.board_uid
                else:
                    assert get_current_board_uid() is None
            mock_response = MagicMock()
            return mock_response

        return mock_call_next

    @pytest.mark.asyncio
    async def test_extract_valid_board_uid(self, middleware):
        """Test extraction of valid board UID from URL."""
        # Create a test database first
        temp_dir = tempfile.mkdtemp()
        old_base_path = db_manager.base_path
        db_manager.base_path = temp_dir

        try:
            board_uid = "test-board"
            db_path = os.path.join(temp_dir, f"{board_uid}.db")
            engine = create_engine(f"sqlite:///{db_path}")
            Base.metadata.create_all(bind=engine)

            # Test valid board extraction
            request = self.create_mock_request(f"/board/{board_uid}/cards")
            call_next = self.create_mock_call_next()

            await middleware.dispatch(request, call_next)

            # Verify board UID was set in request state
            assert request.state.board_uid == board_uid
            # Context should be cleaned up after request
            assert get_current_board_uid() is None

        finally:
            # Cleanup
            db_manager.base_path = old_base_path
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)
            set_current_board_uid(None)

    @pytest.mark.asyncio
    async def test_reject_nonexistent_board(self, middleware):
        """Test rejection of requests to non-existent boards."""
        request = self.create_mock_request("/board/nonexistent-board/auth/login")
        call_next = self.create_mock_call_next()

        # This should return a JSONResponse with 401 status code
        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 401
        assert "not found or access denied" in response.body.decode()

    @pytest.mark.asyncio
    async def test_ignore_invalid_board_uid(self, middleware):
        """Test that invalid board UIDs are ignored."""
        request = self.create_mock_request("/board/board with spaces/cards")
        call_next = self.create_mock_call_next(check_context=False)

        await middleware.dispatch(request, call_next)

        # Board UID should not be set for invalid UIDs
        assert get_current_board_uid() is None
        # Request state should not have board_uid attribute for invalid UIDs
        assert not hasattr(request.state, "board_uid")

    @pytest.mark.asyncio
    async def test_no_board_uid_in_path(self, middleware):
        """Test requests without board UID in path."""
        request = self.create_mock_request("/health")
        call_next = self.create_mock_call_next(check_context=False)

        await middleware.dispatch(request, call_next)

        # Board UID should remain None
        assert get_current_board_uid() is None

    @pytest.mark.asyncio
    async def test_context_cleanup_after_request(self, middleware):
        """Test that board context is cleaned up after request."""
        request = self.create_mock_request("/board/test-board/cards")
        call_next = self.create_mock_call_next()

        # Create a test database first
        temp_dir = tempfile.mkdtemp()
        old_base_path = db_manager.base_path
        db_manager.base_path = temp_dir

        try:
            board_uid = "test-board"
            db_path = os.path.join(temp_dir, f"{board_uid}.db")
            engine = create_engine(f"sqlite:///{db_path}")
            Base.metadata.create_all(bind=engine)

            await middleware.dispatch(request, call_next)

            # Context should be cleaned up after request
            assert get_current_board_uid() is None

        finally:
            # Cleanup
            db_manager.base_path = old_base_path
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_handles_value_error_from_manager(self, middleware):
        """Test handling of ValueError from multi-database manager."""
        request = self.create_mock_request("/board/nonexistent-board/cards")
        call_next = self.create_mock_call_next()

        # This should return a JSONResponse with 401 status code
        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 401
        assert "not found or access denied" in response.body.decode()

    def test_board_database_exists_true(self, middleware, create_test_database):
        """Test _board_database_exists returns True for existing database."""
        board_uid = "existing-board"
        create_test_database(board_uid)

        assert middleware._board_database_exists(board_uid) is True

    def test_board_database_exists_false(self, middleware):
        """Test _board_database_exists returns False for non-existing database."""
        board_uid = "non-existing-board"

        assert middleware._board_database_exists(board_uid) is False

    def test_valid_board_uid_patterns(self, middleware):
        """Test validation of various valid board UID patterns."""
        valid_uids = [
            "board1",
            "test-board",
            "a",
            "BOARD123",
            "test-board-123",
            "my-project-2024",
            "123-board",
            "project-alpha",
        ]

        for uid in valid_uids:
            assert middleware._is_valid_board_uid(uid), f"Should consider '{uid}' as valid"

    def test_invalid_board_uid_patterns(self, middleware):
        """Test validation of various invalid board UID patterns."""
        invalid_uids = [
            "",  # Empty
            "board with spaces",  # Spaces
            "board@123",  # Special character
            "board.test",  # Dot not allowed
            "board_123",  # Underscore not allowed
            "team_alpha",  # Underscore not allowed
            "board#tag",  # Special character
            "board/invalid",  # Forward slash
            "board\\invalid",  # Backslash
            "a" * 51,  # Too long (51 characters)
            "../../../etc/passwd",  # Path traversal attempt
            "board|pipe",  # Pipe character
            "board<angle>",  # Angle brackets
            "board[bracket]",  # Brackets
            "board{brace}",  # Braces
        ]

        for uid in invalid_uids:
            assert not middleware._is_valid_board_uid(uid), f"Should consider '{uid}' as invalid"

    def test_max_length_validation(self, middleware):
        """Test maximum length validation (50 characters)."""
        # Exactly 50 characters - should be valid
        valid_uid = "a" * 50
        assert middleware._is_valid_board_uid(valid_uid) is True

        # 51 characters - should be invalid
        invalid_uid = "a" * 51
        assert middleware._is_valid_board_uid(invalid_uid) is False

    def test_edge_cases(self, middleware):
        """Test edge cases for board UID validation."""
        # Single character should be valid
        assert middleware._is_valid_board_uid("a") is True

        # Numbers only should be valid
        assert middleware._is_valid_board_uid("123") is True

        # Mixed case should be valid
        assert middleware._is_valid_board_uid("Board123") is True

        # Underscore should be invalid
        assert middleware._is_valid_board_uid("test_board") is False

        # Hyphen should be valid
        assert middleware._is_valid_board_uid("test-board") is True

        # Dot should be invalid
        assert middleware._is_valid_board_uid("test.board") is False


class TestGetBoardUidFromRequest:
    """Test cases for the get_board_uid_from_request utility function."""

    def test_extract_from_request_state(self):
        """Test extraction from request.state when available."""
        request = MagicMock()
        request.state.board_uid = "test-board"
        request.url.path = "/some/path"

        result = get_board_uid_from_request(request)
        assert result == "test-board"

    def test_extract_from_path_when_state_empty(self):
        """Test extraction from path when state is empty."""
        request = MagicMock()
        request.state = MagicMock()
        delattr(request.state, "board_uid")  # Remove board_uid if it exists
        request.url.path = "/board/test-board/cards"

        result = get_board_uid_from_request(request)
        assert result == "test-board"

    def test_return_none_when_no_board_uid(self):
        """Test that None is returned when no board UID is present."""
        request = MagicMock()
        request.state = MagicMock()
        delattr(request.state, "board_uid")  # Remove board_uid if it exists
        request.url.path = "/health"

        result = get_board_uid_from_request(request)
        assert result is None

    def test_ignore_invalid_board_uid_in_path(self):
        """Test that invalid board UIDs in path are ignored."""
        request = MagicMock()
        request.state = MagicMock()
        delattr(request.state, "board_uid")  # Remove board_uid if it exists
        request.url.path = "/board/invalid board with spaces/cards"

        result = get_board_uid_from_request(request)
        assert result is None

    def test_extract_board_uid_from_complex_path(self):
        """Test extraction from complex paths."""
        test_cases = [
            ("/board/project-alpha/auth/login", "project-alpha"),
            ("/board/team-beta/cards/123", "team-beta"),
            ("/board/test-board-2024/lists/5/items", "test-board-2024"),
            ("/board/123/boards", "123"),
            ("/api/v1/board/abc", None),  # Board not at start
            ("/board/abc", None),  # No trailing slash, invalid according to pattern
            ("/board/abc/", "abc"),  # With trailing slash
        ]

        for path, expected in test_cases:
            request = MagicMock()
            request.state = MagicMock()
            delattr(request.state, "board_uid")
            request.url.path = path

            result = get_board_uid_from_request(request)
            assert result == expected, f"Failed for path: {path}"
