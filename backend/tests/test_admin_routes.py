"""Tests for the admin routes functionality."""

import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from app.main import app
from app.multi_database import db_manager


class TestAdminRoutes:
    """Test cases for the admin routes."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary directory for test databases."""
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            old_base_path = db_manager.base_path
            db_manager.base_path = temp_dir
            yield temp_dir
            db_manager.base_path = old_base_path

    @pytest.fixture
    def mock_api_key(self):
        """Mock admin API key for testing."""
        return "test-admin-api-key-12345"

    @pytest.fixture
    def set_api_key_env(self, mock_api_key):
        """Set API key environment variable."""
        with patch.dict(os.environ, {"YAKA_ADMIN_API_KEY": mock_api_key}):
            yield

    def create_auth_headers(self, api_key):
        """Create authorization headers for API requests."""
        return {"Authorization": f"Bearer {api_key}"}

    def test_list_boards_no_auth_required(self, client, temp_data_dir):
        """Test that listing boards does not require authentication."""
        # Create a test database
        board_uid = "test-board"
        db_path = os.path.join(temp_data_dir, f"{board_uid}.db")
        from sqlalchemy import create_engine
        from app.database import Base

        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(bind=engine)
        engine.dispose()  # Close the connection properly

        response = client.get("/admin/boards")

        assert response.status_code == 200
        data = response.json()
        assert "boards" in data
        assert len(data["boards"]) >= 1

        # Check that our test board is listed
        board_uids = [board["board_uid"] for board in data["boards"]]
        assert board_uid in board_uids

    def test_list_boards_empty_directory(self, client, temp_data_dir):
        """Test listing boards when no boards exist."""
        response = client.get("/admin/boards")

        assert response.status_code == 200
        data = response.json()
        assert data["boards"] == []

    def test_get_board_info_existing(self, client, temp_data_dir):
        """Test getting info for an existing board."""
        # Create a test database
        board_uid = "existing-board"
        db_path = os.path.join(temp_data_dir, f"{board_uid}.db")
        from sqlalchemy import create_engine
        from app.database import Base

        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(bind=engine)
        engine.dispose()  # Close the connection properly

        response = client.get(f"/admin/boards/{board_uid}")

        assert response.status_code == 200
        data = response.json()
        assert data["board_uid"] == board_uid
        assert data["exists"] is True
        # Check that the path ends with the expected filename (could be absolute or relative)
        assert data["database_path"].endswith(f"{board_uid}.db")
        assert data["access_url"] == f"/board/{board_uid}/"

    def test_get_board_info_nonexistent(self, client):
        """Test getting info for a non-existent board."""
        board_uid = "nonexistent-board"

        response = client.get(f"/admin/boards/{board_uid}")

        assert response.status_code == 200
        data = response.json()
        assert data["board_uid"] == board_uid
        assert data["exists"] is False
        assert data["database_path"] is None
        assert data["access_url"] is None

    def test_create_board_success(self, client, temp_data_dir, set_api_key_env, mock_api_key):
        """Test successful board creation."""
        board_uid = "new-test-board"
        headers = self.create_auth_headers(mock_api_key)

        response = client.post("/admin/boards", json={"board_uid": board_uid}, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert data["message"] == f"Board '{board_uid}' created successfully"
        assert data["board_uid"] == board_uid
        assert "database_path" in data
        assert "access_url" in data
        assert data["access_url"] == f"/board/{board_uid}/"

        # Verify database file was created
        db_path = os.path.join(temp_data_dir, f"{board_uid}.db")
        assert os.path.exists(db_path)

    def test_create_board_invalid_uid(self, client, set_api_key_env, mock_api_key):
        """Test board creation with invalid board UID."""
        invalid_uid = "board with spaces"
        headers = self.create_auth_headers(mock_api_key)

        response = client.post("/admin/boards", json={"board_uid": invalid_uid}, headers=headers)

        assert response.status_code == 400
        assert "alphanumeric" in response.json()["detail"].lower()

    def test_create_board_already_exists(self, client, temp_data_dir, set_api_key_env, mock_api_key):
        """Test board creation when board already exists."""
        board_uid = "existing-board"

        # Create the database first
        db_path = os.path.join(temp_data_dir, f"{board_uid}.db")
        from sqlalchemy import create_engine
        from app.database import Base

        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(bind=engine)
        engine.dispose()  # Close the connection properly

        headers = self.create_auth_headers(mock_api_key)

        response = client.post("/admin/boards", json={"board_uid": board_uid}, headers=headers)

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_create_board_no_api_key(self, client):
        """Test board creation without API key environment variable set."""
        board_uid = "test-board"
        headers = {"Authorization": "Bearer some-key"}

        # Ensure no API key is set
        with patch.dict(os.environ, {}, clear=False):
            if "YAKA_ADMIN_API_KEY" in os.environ:
                del os.environ["YAKA_ADMIN_API_KEY"]
            response = client.post("/admin/boards", json={"board_uid": board_uid}, headers=headers)

        assert response.status_code == 503
        assert "not configured" in response.json()["detail"]

    def test_create_board_invalid_api_key(self, client, set_api_key_env):
        """Test board creation with invalid API key."""
        board_uid = "test-board"
        headers = {"Authorization": "Bearer invalid-key"}

        response = client.post("/admin/boards", json={"board_uid": board_uid}, headers=headers)

        assert response.status_code == 401
        assert "Invalid or missing admin API key" in response.json()["detail"]

    def test_create_board_no_auth_header(self, client, set_api_key_env):
        """Test board creation without authorization header."""
        board_uid = "test-board"

        response = client.post("/admin/boards", json={"board_uid": board_uid})

        assert response.status_code == 403  # FastAPI HTTPBearer returns 403 for missing Bearer token

    def test_delete_board_success(self, client, temp_data_dir, set_api_key_env, mock_api_key):
        """Test successful board deletion."""
        board_uid = "board-to-delete"

        # Create the database first
        db_path = os.path.join(temp_data_dir, f"{board_uid}.db")
        from sqlalchemy import create_engine
        from app.database import Base

        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(bind=engine)
        engine.dispose()  # Close the connection properly

        headers = self.create_auth_headers(mock_api_key)

        response = client.delete(f"/admin/boards/{board_uid}", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert f"Board '{board_uid}' archived successfully" in data["message"]
        assert "archived_path" in data

        # Verify database file was moved (not in original location)
        assert not os.path.exists(db_path)

    def test_delete_nonexistent_board(self, client, set_api_key_env, mock_api_key):
        """Test deletion of non-existent board."""
        board_uid = "nonexistent-board"
        headers = self.create_auth_headers(mock_api_key)

        response = client.delete(f"/admin/boards/{board_uid}", headers=headers)

        assert response.status_code == 404
        assert "does not exist" in response.json()["detail"]

    def test_delete_default_board_forbidden(self, client, set_api_key_env, mock_api_key):
        """Test that deleting default 'yaka' board is forbidden."""
        board_uid = "yaka"
        headers = self.create_auth_headers(mock_api_key)

        response = client.delete(f"/admin/boards/{board_uid}", headers=headers)

        assert response.status_code == 403
        assert "Cannot delete default board" in response.json()["detail"]

    def test_delete_board_no_api_key(self, client):
        """Test board deletion without API key environment variable set."""
        board_uid = "test-board"
        headers = {"Authorization": "Bearer some-key"}

        # Ensure no API key is set
        with patch.dict(os.environ, {}, clear=False):
            if "YAKA_ADMIN_API_KEY" in os.environ:
                del os.environ["YAKA_ADMIN_API_KEY"]
            response = client.delete(f"/admin/boards/{board_uid}", headers=headers)

        assert response.status_code == 503
        assert "not configured" in response.json()["detail"]

    def test_delete_board_invalid_api_key(self, client, set_api_key_env):
        """Test board deletion with invalid API key."""
        board_uid = "test-board"
        headers = {"Authorization": "Bearer invalid-key"}

        response = client.delete(f"/admin/boards/{board_uid}", headers=headers)

        assert response.status_code == 401
        assert "Invalid or missing admin API key" in response.json()["detail"]


class TestAdminRoutesSecurity:
    """Test security aspects of admin routes."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_api_key(self):
        """Mock admin API key for testing."""
        return "test-admin-api-key-12345"

    @pytest.fixture
    def set_api_key_env(self, mock_api_key):
        """Set API key environment variable."""
        with patch.dict(os.environ, {"YAKA_ADMIN_API_KEY": mock_api_key}):
            yield

    def test_unauthorized_access_to_protected_endpoints(self, client):
        """Test that protected endpoints reject unauthorized access."""
        protected_endpoints = [
            ("POST", "/admin/boards", {"board_uid": "test"}),
            ("DELETE", "/admin/boards/test", None),
        ]

        for method, endpoint, data in protected_endpoints:
            if data:
                response = client.request(method, endpoint, json=data)
            else:
                response = client.request(method, endpoint)

            # Should return 403 for missing authorization (HTTPBearer behavior)
            assert response.status_code == 403

    def test_sql_injection_prevention(self, client, set_api_key_env):
        """Test that SQL injection attempts are prevented through validation."""
        api_key = os.getenv("YAKA_ADMIN_API_KEY")
        headers = {"Authorization": f"Bearer {api_key}"}

        # Test various SQL injection attempts
        malicious_uids = [
            "'; DROP TABLE users; --",
            "board' OR '1'='1",
            'board"; DELETE FROM cards; --',
            "../../../etc/passwd",
            "board'; DROP TABLE users; --",
            "board' UNION SELECT * FROM users --",
        ]

        for malicious_uid in malicious_uids:
            response = client.post("/admin/boards", json={"board_uid": malicious_uid}, headers=headers)

            # Should be rejected due to validation
            assert response.status_code == 400

    def test_path_traversal_prevention(self, client, set_api_key_env):
        """Test that path traversal attempts are prevented."""
        api_key = os.getenv("YAKA_ADMIN_API_KEY")
        headers = {"Authorization": f"Bearer {api_key}"}

        # Test path traversal attempts
        traversal_uids = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config",
            "/etc/passwd",
            "C:\\Windows\\System32\\drivers\\etc\\hosts",
        ]

        for traversal_uid in traversal_uids:
            response = client.post("/admin/boards", json={"board_uid": traversal_uid}, headers=headers)

            # Should be rejected due to validation
            assert response.status_code == 400


class TestAdminRoutesEdgeCases:
    """Test edge cases and error handling for admin routes."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary directory for test databases."""
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            old_base_path = db_manager.base_path
            db_manager.base_path = temp_dir
            yield temp_dir
            db_manager.base_path = old_base_path

    @pytest.fixture
    def mock_api_key(self):
        """Mock admin API key for testing."""
        return "test-admin-api-key-12345"

    @pytest.fixture
    def set_api_key_env(self, mock_api_key):
        """Set API key environment variable."""
        with patch.dict(os.environ, {"YAKA_ADMIN_API_KEY": mock_api_key}):
            yield

    def test_create_board_with_special_characters(self, client, temp_data_dir, set_api_key_env):
        """Test board creation with various special characters."""
        api_key = os.getenv("YAKA_ADMIN_API_KEY")
        headers = {"Authorization": f"Bearer {api_key}"}

        # Test valid characters
        valid_uids = [
            "board-with-dashes",
            "123-board",
            "BOARD-UPPERCASE",
            "a",  # Single character
            "a" * 50,  # Maximum length
            "project-alpha",
            "test-board-123",
        ]

        for uid in valid_uids:
            response = client.post("/admin/boards", json={"board_uid": uid}, headers=headers)
            assert response.status_code == 201, f"Failed for valid UID: {uid}"

            # Clean up immediately to avoid database lock issues on Windows
            if response.status_code == 201:
                client.delete(f"/admin/boards/{uid}", headers=headers)

    def test_create_board_too_long(self, client, set_api_key_env):
        """Test board creation with too long board UID."""
        api_key = os.getenv("YAKA_ADMIN_API_KEY")
        headers = {"Authorization": f"Bearer {api_key}"}

        # Create a board UID that's too long (51 characters)
        long_uid = "a" * 51

        response = client.post("/admin/boards", json={"board_uid": long_uid}, headers=headers)

        assert response.status_code == 400

    def test_empty_board_uid(self, client, set_api_key_env):
        """Test board creation with empty board UID."""
        api_key = os.getenv("YAKA_ADMIN_API_KEY")
        headers = {"Authorization": f"Bearer {api_key}"}

        response = client.post("/admin/boards", json={"board_uid": ""}, headers=headers)

        assert response.status_code == 400

    def test_malformed_json_request(self, client, set_api_key_env):
        """Test handling of malformed JSON requests."""
        api_key = os.getenv("YAKA_ADMIN_API_KEY")
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        # Send malformed JSON
        response = client.post("/admin/boards", data='{"board_uid": "test", invalid_json}', headers=headers)

        assert response.status_code == 422  # Unprocessable Entity

    def test_missing_board_uid_field(self, client, set_api_key_env):
        """Test request missing the board_uid field."""
        api_key = os.getenv("YAKA_ADMIN_API_KEY")
        headers = {"Authorization": f"Bearer {api_key}"}

        response = client.post("/admin/boards", json={"wrong_field": "test"}, headers=headers)

        assert response.status_code == 422  # Validation error
