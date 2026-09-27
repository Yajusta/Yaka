"""Tests for the admin routes functionality."""

import os
from unittest.mock import patch

import pytest
from app.main import app
from app.multi_database import db_manager
from fastapi.testclient import TestClient


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test databases."""
    import tempfile

    from app.multi_database import _engines, _sessions, evict_board

    with tempfile.TemporaryDirectory() as temp_dir:
        old_base_path = db_manager.base_path
        db_manager.base_path = temp_dir
        yield temp_dir

        # Dispose all engines to release database locks before cleanup
        for board_uid in {*_engines, *_sessions}:
            evict_board(board_uid)

        db_manager.base_path = old_base_path


class TestAdminRoutes:
    """Test cases for the admin routes."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_api_key(self):
        """Mock admin API key for testing."""
        return "test-admin-api-key-0123456789abcdef"

    @pytest.fixture
    def set_api_key_env(self, mock_api_key):
        """Set API key environment variable."""
        with patch.dict(os.environ, {"YAKA_ADMIN_API_KEY": mock_api_key}):
            yield

    def create_auth_headers(self, api_key):
        """Create authorization headers for API requests."""
        return {"Authorization": f"Bearer {api_key}"}

    def test_list_boards_auth_required(self, client, temp_data_dir):
        """Test that listing boards requires authentication."""
        # Create a test database
        board_uid = "test-board"
        db_path = os.path.join(temp_data_dir, f"{board_uid}.db")
        from app.database import Base
        from sqlalchemy import create_engine

        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(bind=engine)
        engine.dispose()  # Close the connection properly

        response = client.get("/admin/boards")

        assert response.status_code == 401

    def test_get_board_info_existing(
        self, client, temp_data_dir, set_api_key_env, mock_api_key
    ):
        """Test getting info for an existing board."""
        # Create a test database
        board_uid = "existing-board"
        db_path = os.path.join(temp_data_dir, f"{board_uid}.db")
        from app.database import Base
        from sqlalchemy import create_engine

        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(bind=engine)
        engine.dispose()  # Close the connection properly

        response = client.get(
            f"/admin/boards/{board_uid}", headers=self.create_auth_headers(mock_api_key)
        )

        assert response.status_code == 200
        data = response.json()
        assert data["board_uid"] == board_uid
        assert data["exists"] is True
        # The server-side path is no longer disclosed
        assert "database_path" not in data
        assert data["access_url"] == f"/board/{board_uid}/"

    def test_get_board_info_nonexistent(self, client, set_api_key_env, mock_api_key):
        """Test getting info for a non-existent board."""
        board_uid = "nonexistent-board"

        response = client.get(
            f"/admin/boards/{board_uid}", headers=self.create_auth_headers(mock_api_key)
        )

        assert response.status_code == 200
        data = response.json()
        assert data["board_uid"] == board_uid
        assert data["exists"] is False
        assert "database_path" not in data
        assert data["access_url"] is None

    def test_get_board_info_invalid_api_key(self, client, set_api_key_env):
        """Board info rejects an invalid admin API key (missing key: see security tests)."""
        response = client.get(
            "/admin/boards/some-board", headers={"Authorization": "Bearer invalid-key"}
        )
        assert response.status_code == 401

    @pytest.mark.parametrize(
        ("method", "url", "json"),
        [
            ("POST", "/admin/boards", {"board_uid": "test-board"}),
            ("DELETE", "/admin/boards/test-board", None),
            ("GET", "/admin/boards/test-board", None),
        ],
    )
    def test_no_api_key_configured(self, client, monkeypatch, method, url, json):
        """Admin routes are unavailable when no admin API key is configured."""
        monkeypatch.delenv("YAKA_ADMIN_API_KEY", raising=False)

        response = client.request(
            method, url, json=json, headers={"Authorization": "Bearer some-key"}
        )

        assert response.status_code == 503
        assert "not configured" in response.json()["detail"]

    def test_create_board_success(
        self, client, temp_data_dir, set_api_key_env, mock_api_key
    ):
        """Test successful board creation."""
        board_uid = "new-test-board"
        headers = self.create_auth_headers(mock_api_key)

        response = client.post(
            "/admin/boards", json={"board_uid": board_uid}, headers=headers
        )

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

        response = client.post(
            "/admin/boards", json={"board_uid": invalid_uid}, headers=headers
        )

        assert response.status_code == 400
        assert "alphanumeric" in response.json()["detail"].lower()

    def test_create_board_already_exists(
        self, client, temp_data_dir, set_api_key_env, mock_api_key
    ):
        """Test board creation when board already exists."""
        board_uid = "existing-board"

        # Create the database first
        db_path = os.path.join(temp_data_dir, f"{board_uid}.db")
        from app.database import Base
        from sqlalchemy import create_engine

        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(bind=engine)
        engine.dispose()  # Close the connection properly

        headers = self.create_auth_headers(mock_api_key)

        response = client.post(
            "/admin/boards", json={"board_uid": board_uid}, headers=headers
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_create_board_invalid_api_key(self, client, set_api_key_env):
        """Test board creation with invalid API key."""
        board_uid = "test-board"
        headers = {"Authorization": "Bearer invalid-key"}

        response = client.post(
            "/admin/boards", json={"board_uid": board_uid}, headers=headers
        )

        assert response.status_code == 401
        assert "Invalid or missing admin API key" in response.json()["detail"]

    def test_create_board_no_auth_header(self, client, set_api_key_env):
        """Test board creation without authorization header."""
        board_uid = "test-board"

        response = client.post("/admin/boards", json={"board_uid": board_uid})

        assert (
            response.status_code == 401
        )  # FastAPI HTTPBearer renvoie 401 quand l'en-tête Bearer est absent

    def test_delete_board_success(
        self, client, temp_data_dir, set_api_key_env, mock_api_key
    ):
        """Test successful board deletion."""
        board_uid = "board-to-delete"

        # Create the database first
        db_path = os.path.join(temp_data_dir, f"{board_uid}.db")
        from app.database import Base
        from sqlalchemy import create_engine

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

    def test_delete_default_board_forbidden(
        self, client, set_api_key_env, mock_api_key
    ):
        """Test that deleting default 'yaka' board is forbidden."""
        board_uid = "yaka"
        headers = self.create_auth_headers(mock_api_key)

        response = client.delete(f"/admin/boards/{board_uid}", headers=headers)

        assert response.status_code == 403
        assert "Cannot delete default board" in response.json()["detail"]

    def test_delete_board_invalid_api_key(self, client, set_api_key_env):
        """Test board deletion with invalid API key."""
        board_uid = "test-board"
        headers = {"Authorization": "Bearer invalid-key"}

        response = client.delete(f"/admin/boards/{board_uid}", headers=headers)

        assert response.status_code == 401
        assert "Invalid or missing admin API key" in response.json()["detail"]

    def test_recreated_board_uses_fresh_database(
        self, client, temp_data_dir, set_api_key_env, mock_api_key
    ):
        """A board deleted then recreated without restart gets a fresh database."""
        from app.models import User
        from app.multi_database import get_board_db
        from app.schemas import UserCreate
        from app.services.user import create_user

        board_uid = "recreated-board"
        headers = self.create_auth_headers(mock_api_key)
        credentials = {"username": "old-member@example.com", "password": "OldMember-1"}

        response = client.post(
            "/admin/boards", json={"board_uid": board_uid}, headers=headers
        )
        assert response.status_code == 201

        # A member of the first board, logged in (the board engine is now cached)
        with get_board_db(board_uid) as db:
            create_user(
                db,
                UserCreate(
                    email=credentials["username"],
                    password=credentials["password"],
                    display_name="Old member",
                    language="fr",
                ),
            )
        login = client.post(f"/board/{board_uid}/auth/login", data=credentials)
        assert login.status_code == 200
        old_token = login.json()["access_token"]

        response = client.delete(f"/admin/boards/{board_uid}", headers=headers)
        assert response.status_code == 200
        response = client.post(
            "/admin/boards", json={"board_uid": board_uid}, headers=headers
        )
        assert response.status_code == 201

        # The recreated board is a new, empty database
        with get_board_db(board_uid) as db:
            assert db.query(User).count() == 0

        # Former members can neither log in nor reuse their session
        response = client.post(f"/board/{board_uid}/auth/login", data=credentials)
        assert response.status_code == 401
        response = client.get(
            f"/board/{board_uid}/auth/me",
            headers={"Authorization": f"Bearer {old_token}"},
        )
        assert response.status_code == 401

        # Re-added with the same email (hence the same id), the member's old
        # session token is still rejected
        with get_board_db(board_uid) as db:
            create_user(
                db,
                UserCreate(
                    email=credentials["username"],
                    password="NewMember-1",
                    display_name="New member",
                    language="fr",
                ),
            )
        response = client.get(
            f"/board/{board_uid}/auth/me",
            headers={"Authorization": f"Bearer {old_token}"},
        )
        assert response.status_code == 401

    def test_create_board_error_is_generic(
        self, client, temp_data_dir, set_api_key_env, mock_api_key
    ):
        """An unexpected error while creating a board does not leak its details."""
        with patch(
            "app.routers.admin.create_engine",
            side_effect=RuntimeError("secret internal detail"),
        ):
            response = client.post(
                "/admin/boards",
                json={"board_uid": "failing-board"},
                headers=self.create_auth_headers(mock_api_key),
            )

        assert response.status_code == 500
        assert response.json() == {"detail": "Error creating board"}

    def test_delete_board_error_is_generic(
        self, client, temp_data_dir, set_api_key_env, mock_api_key
    ):
        """An unexpected error while archiving a board does not leak its details."""
        board_uid = "failing-delete"
        headers = self.create_auth_headers(mock_api_key)
        response = client.post(
            "/admin/boards", json={"board_uid": board_uid}, headers=headers
        )
        assert response.status_code == 201

        with patch("os.rename", side_effect=OSError("secret internal detail")):
            response = client.delete(f"/admin/boards/{board_uid}", headers=headers)

        assert response.status_code == 500
        assert response.json() == {"detail": "Error archiving board"}
        # A failed archive leaves the board in place and no stray copy behind
        assert db_manager.ensure_database_exists(board_uid)
        assert not os.listdir(os.path.join(temp_data_dir, "deleted"))

    def test_create_board_lost_race_keeps_winner_file(
        self, client, temp_data_dir, set_api_key_env, mock_api_key
    ):
        """A create losing the race for the same uid gets 409 and deletes nothing."""
        board_uid = "raced-board"
        headers = self.create_auth_headers(mock_api_key)
        # The concurrent winner created the file after the loser's checks
        winner_path = db_manager.get_database_path(board_uid)
        with open(winner_path, "wb"):
            pass

        response = client.post(
            "/admin/boards", json={"board_uid": board_uid}, headers=headers
        )

        assert response.status_code == 409
        assert os.path.exists(winner_path)

    @pytest.mark.parametrize("board_uid", ["Yaka", "YAKA"])
    def test_create_default_board_other_case_rejected(
        self, client, temp_data_dir, set_api_key_env, mock_api_key, board_uid
    ):
        """A board that delete_board would refuse to archive cannot be created."""
        response = client.post(
            "/admin/boards",
            json={"board_uid": board_uid},
            headers=self.create_auth_headers(mock_api_key),
        )
        assert response.status_code == 409
        assert not db_manager.ensure_database_exists(board_uid)

    def test_create_board_failure_removes_partial_file(
        self, client, temp_data_dir, set_api_key_env, mock_api_key
    ):
        """A failed creation leaves no half-created database behind (retry possible)."""
        board_uid = "half-created"
        headers = self.create_auth_headers(mock_api_key)
        with patch(
            "app.routers.admin.db_manager._initialize_alembic_version",
            side_effect=RuntimeError("disk full"),
        ):
            response = client.post(
                "/admin/boards", json={"board_uid": board_uid}, headers=headers
            )
        assert response.status_code == 500
        assert not db_manager.ensure_database_exists(board_uid)
        # Nor any leftover temporary build file
        assert os.listdir(temp_data_dir) == []

        response = client.post(
            "/admin/boards", json={"board_uid": board_uid}, headers=headers
        )
        assert response.status_code == 201

    def test_create_board_not_visible_until_complete(
        self, client, temp_data_dir, set_api_key_env, mock_api_key
    ):
        """The board file only appears once its schema is complete."""
        board_uid = "in-progress"
        real_init = db_manager._initialize_alembic_version
        seen_during_build = []

        def init_and_observe(engine):
            seen_during_build.append(db_manager.ensure_database_exists(board_uid))
            return real_init(engine)

        with patch(
            "app.routers.admin.db_manager._initialize_alembic_version",
            side_effect=init_and_observe,
        ):
            response = client.post(
                "/admin/boards",
                json={"board_uid": board_uid},
                headers=self.create_auth_headers(mock_api_key),
            )

        assert response.status_code == 201
        assert seen_during_build == [False]
        assert os.listdir(temp_data_dir) == [f"{board_uid}.db"]

    def test_create_board_race_during_build_keeps_winner(
        self, client, temp_data_dir, set_api_key_env, mock_api_key
    ):
        """A concurrent creation finishing first wins; the loser gets 409."""
        board_uid = "raced-during-build"
        winner_path = db_manager.get_database_path(board_uid)
        real_init = db_manager._initialize_alembic_version

        def winner_publishes_meanwhile(engine):
            with open(winner_path, "wb") as f:
                f.write(b"winner")
            return real_init(engine)

        with patch(
            "app.routers.admin.db_manager._initialize_alembic_version",
            side_effect=winner_publishes_meanwhile,
        ):
            response = client.post(
                "/admin/boards",
                json={"board_uid": board_uid},
                headers=self.create_auth_headers(mock_api_key),
            )

        assert response.status_code == 409
        with open(winner_path, "rb") as f:
            assert f.read() == b"winner"
        assert os.listdir(temp_data_dir) == [f"{board_uid}.db"]

    def test_delete_recreate_delete_keeps_both_archives(
        self, client, temp_data_dir, set_api_key_env, mock_api_key
    ):
        """Two archives of the same board made in quick succession do not collide."""
        board_uid = "archived-twice"
        headers = self.create_auth_headers(mock_api_key)
        for _ in range(2):
            response = client.post(
                "/admin/boards", json={"board_uid": board_uid}, headers=headers
            )
            assert response.status_code == 201
            response = client.delete(f"/admin/boards/{board_uid}", headers=headers)
            assert response.status_code == 200

        assert len(os.listdir(os.path.join(temp_data_dir, "deleted"))) == 2

    def test_delete_default_board_is_case_insensitive(
        self, client, temp_data_dir, set_api_key_env, mock_api_key
    ):
        """The default board cannot be archived through another letter case."""
        response = client.delete(
            "/admin/boards/YAKA", headers=self.create_auth_headers(mock_api_key)
        )
        assert response.status_code == 403

    @pytest.mark.parametrize("method", ["GET", "DELETE"])
    def test_invalid_board_uid_rejected(
        self, client, temp_data_dir, set_api_key_env, mock_api_key, method
    ):
        """Board info and deletion reject UIDs the middleware would never serve."""
        response = client.request(
            method,
            "/admin/boards/bad.board",
            headers=self.create_auth_headers(mock_api_key),
        )
        assert response.status_code == 400

    def test_delete_board_evicts_engine_cached_during_move(
        self, client, temp_data_dir, set_api_key_env, mock_api_key
    ):
        """An engine cached by a concurrent request during the move is dropped too."""
        from app.multi_database import _engines

        board_uid = "racing-board"
        headers = self.create_auth_headers(mock_api_key)
        response = client.post(
            "/admin/boards", json={"board_uid": board_uid}, headers=headers
        )
        assert response.status_code == 201

        real_rename = os.rename

        def move_after_concurrent_request(src, dst):
            # A request reaches the board between the eviction and the move
            db_manager.get_engine(board_uid).dispose()
            return real_rename(src, dst)

        with patch("os.rename", side_effect=move_after_concurrent_request):
            response = client.delete(f"/admin/boards/{board_uid}", headers=headers)

        assert response.status_code == 200
        assert board_uid not in _engines

    def test_cached_engine_does_not_recreate_archived_file(self, temp_data_dir):
        """A stale engine cannot recreate an empty database at the archived path."""
        from sqlalchemy import create_engine
        from sqlalchemy.exc import OperationalError

        board_uid = "stale-engine"
        db_path = db_manager.get_database_path(board_uid)
        bootstrap = create_engine(f"sqlite:///{db_path}")
        bootstrap.connect().close()
        bootstrap.dispose()

        engine = db_manager.get_engine(board_uid)
        engine.dispose()
        os.remove(db_path)

        with pytest.raises(OperationalError):
            engine.connect()
        assert not os.path.exists(db_path)

    def test_demo_reset_error_is_generic(self, client):
        """An unexpected error during the demo reset does not leak its details."""
        with (
            patch("app.main.is_demo_mode", return_value=True),
            patch(
                "app.main.reset_database",
                side_effect=RuntimeError("secret internal detail"),
            ),
        ):
            response = client.post("/demo/reset")

        assert response.status_code == 500
        assert response.json() == {"detail": "Error resetting database"}


class TestAdminRoutesSecurity:
    """Test security aspects of admin routes."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_api_key(self):
        """Mock admin API key for testing."""
        return "test-admin-api-key-0123456789abcdef"

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
            ("GET", "/admin/boards/test", None),
        ]

        for method, endpoint, data in protected_endpoints:
            if data:
                response = client.request(method, endpoint, json=data)
            else:
                response = client.request(method, endpoint)

            # 401 attendu quand l'autorisation manque (comportement HTTPBearer)
            assert response.status_code == 401

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
            response = client.post(
                "/admin/boards", json={"board_uid": malicious_uid}, headers=headers
            )

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
            response = client.post(
                "/admin/boards", json={"board_uid": traversal_uid}, headers=headers
            )

            # Should be rejected due to validation
            assert response.status_code == 400


class TestAdminRoutesEdgeCases:
    """Test edge cases and error handling for admin routes."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_api_key(self):
        """Mock admin API key for testing."""
        return "test-admin-api-key-0123456789abcdef"

    @pytest.fixture
    def set_api_key_env(self, mock_api_key):
        """Set API key environment variable."""
        with patch.dict(os.environ, {"YAKA_ADMIN_API_KEY": mock_api_key}):
            yield

    def test_create_board_with_special_characters(
        self, client, temp_data_dir, set_api_key_env
    ):
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
            response = client.post(
                "/admin/boards", json={"board_uid": uid}, headers=headers
            )
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

        response = client.post(
            "/admin/boards", json={"board_uid": long_uid}, headers=headers
        )

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
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        # Send malformed JSON
        response = client.post(
            "/admin/boards", data='{"board_uid": "test", invalid_json}', headers=headers
        )

        assert response.status_code == 422  # Unprocessable Entity

    def test_missing_board_uid_field(self, client, set_api_key_env):
        """Test request missing the board_uid field."""
        api_key = os.getenv("YAKA_ADMIN_API_KEY")
        headers = {"Authorization": f"Bearer {api_key}"}

        response = client.post(
            "/admin/boards", json={"wrong_field": "test"}, headers=headers
        )

        assert response.status_code == 422  # Validation error


class TestCreateBoardScript:
    """The provisioning script applies the same rules as the admin route."""

    @pytest.mark.parametrize("board_uid", ["café", "a" * 51, "Yaka", "YAKA"])
    def test_rejected_board_uid(self, temp_data_dir, board_uid):
        from scripts.create_board import create_board_database

        assert create_board_database(board_uid) is False
        assert os.listdir(temp_data_dir) == []

    def test_creates_complete_board(self, temp_data_dir):
        from scripts.create_board import create_board_database

        assert create_board_database("script-board") is True
        assert os.listdir(temp_data_dir) == ["script-board.db"]
        assert create_board_database("script-board") is False
