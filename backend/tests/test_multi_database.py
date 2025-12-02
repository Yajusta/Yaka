"""Tests for the multi-database manager functionality."""

import os
import tempfile

import pytest
from app.database import Base
from app.multi_database import db_manager, get_board_db, get_current_board_uid, set_current_board_uid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class TestMultiDatabaseManager:
    """Test cases for the MultiDatabaseManager class."""

    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary directory for test databases."""
        # Import the global cache variables
        from app.multi_database import _engines, _sessions

        with tempfile.TemporaryDirectory() as temp_dir:
            old_base_path = db_manager.base_path
            old_engines = _engines.copy()
            old_sessions = _sessions.copy()

            db_manager.base_path = temp_dir
            _engines.clear()
            _sessions.clear()

            yield temp_dir

            # Cleanup engines and session locals
            for engine in _engines.values():
                if hasattr(engine, "dispose"):
                    engine.dispose()

            db_manager.base_path = old_base_path
            _engines.update(old_engines)
            _sessions.update(old_sessions)

    def test_get_database_path(self, temp_data_dir):
        """Test database path generation."""
        board_uid = "test-board"
        expected_path = os.path.normpath(os.path.join(temp_data_dir, "test-board.db"))
        actual_path = os.path.normpath(db_manager.get_database_path(board_uid))
        assert actual_path == expected_path

    def test_ensure_database_exists_true(self, temp_data_dir):
        """Test ensure_database_exists returns True when database exists."""
        board_uid = "existing-board"
        db_path = os.path.join(temp_data_dir, f"{board_uid}.db")

        # Create the database file
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(bind=engine)

        assert db_manager.ensure_database_exists(board_uid) is True

    def test_ensure_database_exists_false(self, temp_data_dir):
        """Test ensure_database_exists returns False when database doesn't exist."""
        board_uid = "non-existing-board"
        assert db_manager.ensure_database_exists(board_uid) is False

    def test_get_engine_raises_error_for_nonexistent_database(self, temp_data_dir):
        """Test that get_engine raises ValueError for non-existent database."""
        board_uid = "new-board"

        with pytest.raises(ValueError, match=f"Board '{board_uid}' not found"):
            db_manager.get_engine(board_uid)

    def test_get_engine_returns_existing_engine(self, temp_data_dir):
        """Test that get_engine returns existing engine without creating new one."""
        board_uid = "cached-board"
        db_path = os.path.join(temp_data_dir, f"{board_uid}.db")

        # Create database file first
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(bind=engine)

        # Get engine from manager
        engine1 = db_manager.get_engine(board_uid)
        engine2 = db_manager.get_engine(board_uid)

        # Should return the same engine instance
        assert engine1 is engine2

    def test_get_session_local(self, temp_data_dir):
        """Test session local creation."""
        board_uid = "session-board"
        db_path = os.path.join(temp_data_dir, f"{board_uid}.db")

        # Create database file first
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(bind=engine)

        session_local = db_manager.get_session_local(board_uid)
        assert isinstance(session_local, sessionmaker)

        # Test that we can create a session
        session = session_local()
        assert session is not None
        session.close()

    def test_get_session_local_caching(self, temp_data_dir):
        """Test that session local is cached."""
        board_uid = "cached-session-board"
        db_path = os.path.join(temp_data_dir, f"{board_uid}.db")

        # Create database file first
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(bind=engine)

        session_local1 = db_manager.get_session_local(board_uid)
        session_local2 = db_manager.get_session_local(board_uid)

        # Should return the same session maker instance
        assert session_local1 is session_local2


class TestBoardContext:
    """Test cases for board context management."""

    def test_set_and_get_current_board_uid(self):
        """Test setting and getting current board UID."""
        # Initially should be None
        assert get_current_board_uid() is None

        # Set a board UID
        set_current_board_uid("test-board")
        assert get_current_board_uid() == "test-board"

        # Reset to None
        set_current_board_uid(None)
        assert get_current_board_uid() is None

    def test_get_board_db_context_manager(self):
        """Test get_board_db context manager."""
        # This test verifies the context manager works
        # We don't test actual database operations here

        # With non-existent board, it should raise ValueError when used
        set_current_board_uid("non-existent-board")

        with pytest.raises(ValueError):
            with get_board_db("non-existent-board"):
                pass  # This should not be reached

        # Reset context
        set_current_board_uid(None)


class TestBoardValidation:
    """Test cases for board UID validation."""

    def test_valid_board_uids(self):
        """Test validation of valid board UIDs."""
        from unittest.mock import MagicMock

        from app.utils.board_context import BoardContextMiddleware

        # Create middleware with a mock ASGI app
        mock_app = MagicMock()
        middleware = BoardContextMiddleware(mock_app)

        valid_uids = ["board1", "test-board", "a", "BOARD123", "test-board-123"]

        for uid in valid_uids:
            assert middleware._is_valid_board_uid(uid) is True

    def test_invalid_board_uids(self):
        """Test validation of invalid board UIDs."""
        from unittest.mock import MagicMock

        from app.utils.board_context import BoardContextMiddleware

        # Create middleware with a mock ASGI app
        mock_app = MagicMock()
        middleware = BoardContextMiddleware(mock_app)

        invalid_uids = [
            "",  # Empty
            "board with spaces",  # Spaces
            "board@123",  # Special character
            "board#tag",  # Special character
            "a" * 51,  # Too long (51 characters)
            "../../../etc/passwd",  # Path traversal
            "board|pipe",  # Pipe character
        ]

        for uid in invalid_uids:
            assert middleware._is_valid_board_uid(uid) is False


class TestDatabaseIsolation:
    """Test cases for database isolation between boards."""

    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary directory for test databases."""
        # Import the global cache variables
        from app.multi_database import _engines, _sessions

        with tempfile.TemporaryDirectory() as temp_dir:
            old_base_path = db_manager.base_path
            old_engines = _engines.copy()
            old_sessions = _sessions.copy()

            db_manager.base_path = temp_dir
            _engines.clear()
            _sessions.clear()

            yield temp_dir

            # Cleanup engines and session locals
            for engine in _engines.values():
                if hasattr(engine, "dispose"):
                    engine.dispose()

            db_manager.base_path = old_base_path
            _engines.update(old_engines)
            _sessions.update(old_sessions)

    def test_separate_databases_for_different_boards(self, temp_data_dir):
        """Test that different boards use different databases."""
        board1_uid = "board1"
        board2_uid = "board2"

        # Create databases for both boards
        db_path1 = os.path.join(temp_data_dir, f"{board1_uid}.db")
        db_path2 = os.path.join(temp_data_dir, f"{board2_uid}.db")

        engine1 = create_engine(f"sqlite:///{db_path1}")
        engine2 = create_engine(f"sqlite:///{db_path2}")

        Base.metadata.create_all(bind=engine1)
        Base.metadata.create_all(bind=engine2)

        # Verify they are different files
        assert db_path1 != db_path2
        assert os.path.exists(db_path1)
        assert os.path.exists(db_path2)

        # Verify different engines are returned
        manager_engine1 = db_manager.get_engine(board1_uid)
        manager_engine2 = db_manager.get_engine(board2_uid)

        assert manager_engine1 is not manager_engine2
        assert os.path.normpath(manager_engine1.url.database) == os.path.normpath(db_path1)
        assert os.path.normpath(manager_engine2.url.database) == os.path.normpath(db_path2)

    def test_board_context_isolation(self, temp_data_dir):
        """Test that board context is properly isolated."""
        board1_uid = "context-board1"
        board2_uid = "context-board2"

        # Create databases
        db_path1 = os.path.join(temp_data_dir, f"{board1_uid}.db")
        db_path2 = os.path.join(temp_data_dir, f"{board2_uid}.db")

        engine1 = create_engine(f"sqlite:///{db_path1}")
        engine2 = create_engine(f"sqlite:///{db_path2}")

        Base.metadata.create_all(bind=engine1)
        Base.metadata.create_all(bind=engine2)

        # Test context isolation
        set_current_board_uid(board1_uid)
        assert get_current_board_uid() == board1_uid

        # Should work with current board context
        with get_board_db() as db:
            assert db is not None

        # Switch context
        set_current_board_uid(board2_uid)
        assert get_current_board_uid() == board2_uid

        # Should work with new context
        with get_board_db() as db:
            assert db is not None

        # Reset context
        set_current_board_uid(None)
        assert get_current_board_uid() is None
