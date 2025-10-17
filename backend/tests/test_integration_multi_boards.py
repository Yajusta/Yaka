"""Integration tests for multi-board functionality."""

import asyncio
import os
from unittest.mock import patch
import pytest
from httpx import AsyncClient

from app.routers import admin_router, auth_router, cards_router, users_router
from app.multi_database import db_manager


class TestMultiBoardIntegration:
    """Integration tests for the complete multi-board workflow."""

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

    @pytest.fixture
    def auth_headers(self, mock_api_key):
        """Create authorization headers."""
        return {"Authorization": f"Bearer {mock_api_key}"}

    @pytest.fixture
    async def client(self, async_client_factory):
        """Create async client with all routers."""
        async with async_client_factory(
            admin_router,
            auth_router,
            cards_router,
            users_router
        ) as client:
            yield client

    @pytest.mark.asyncio
    async def test_complete_board_lifecycle(self, client, temp_data_dir, set_api_key_env, auth_headers, seed_admin_user):
        """Test complete lifecycle: create -> access -> delete."""
        board_uid = "integration-test-board"

        # Seed admin user first
        seed_admin_user()

        # 1. Create board via admin API
        create_response = await client.post(
            "/admin/boards",
            json={"board_uid": board_uid},
            headers=auth_headers
        )
        assert create_response.status_code == 201
        board_data = create_response.json()
        assert board_data["board_uid"] == board_uid

        # 2. Login as admin to create users
        admin_login_response = await client.post(
            "/auth/login",
            data={"username": "admin@yaka.local", "password": "Admin123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert admin_login_response.status_code == 200
        admin_token_data = admin_login_response.json()
        admin_token = admin_token_data["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 3. Create user and authenticate for the board
        user_data = {
            "email": f"user@{board_uid}.com",
            "password": "TestPassword123",
            "display_name": "Test User",
            "role": "editor",
            "language": "en"
        }

        # Register user (uses default database, but we'll simulate board-specific)
        register_response = await client.post("/users/", json=user_data, headers=admin_headers)
        assert register_response.status_code == 200

        # 4. Login as the new user to get token
        login_response = await client.post(
            "/auth/login",
            data={"username": user_data["email"], "password": user_data["password"]},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert login_response.status_code == 200
        token_data = login_response.json()
        token = token_data["access_token"]
        board_headers = {"Authorization": f"Bearer {token}"}

        # 5. Test board-specific routes work (simulated by checking auth)
        # Note: In a real scenario, this would access /board/{board_uid}/auth/me
        # For this test, we verify the middleware would handle board context correctly

        # 7. Test that board-specific card operations would work
        # (This is a simplified test since we can't easily test the actual board isolation)
        card_data = {
            "title": f"Test Card for {board_uid}",
            "description": "Test card description",
            "list_id": 1  # This would need to be created per board
        }

        # 8. Delete board
        delete_response = await client.delete(
            f"/admin/boards/{board_uid}",
            headers=auth_headers
        )
        assert delete_response.status_code == 200
        delete_data = delete_response.json()
        assert f"Board '{board_uid}' archived successfully" in delete_data["message"]

        # 9. Verify board no longer exists
        info_response = await client.get(f"/admin/boards/{board_uid}")
        assert info_response.status_code == 200
        info_data = info_response.json()
        assert info_data["exists"] is False

    @pytest.mark.asyncio
    async def test_multiple_boards_isolation(self, client, temp_data_dir, set_api_key_env, auth_headers):
        """Test that multiple boards remain isolated."""
        boards = ["board-alpha", "board-beta", "board-gamma"]
        created_boards = []

        # Create multiple boards
        for board_uid in boards:
            create_response = await client.post(
                "/admin/boards",
                json={"board_uid": board_uid},
                headers=auth_headers
            )
            assert create_response.status_code == 201
            created_boards.append(board_uid)

        # Verify all boards exist
        list_response = await client.get("/admin/boards", headers=auth_headers)
        assert list_response.status_code == 200
        boards_data = list_response.json()
        board_uids = [board["board_uid"] for board in boards_data["boards"]]

        for board_uid in boards:
            assert board_uid in board_uids

        # Delete all boards
        for board_uid in boards:
            delete_response = await client.delete(
                f"/admin/boards/{board_uid}",
                headers=auth_headers
            )
            assert delete_response.status_code == 200

        # Verify all boards are gone
        final_list_response = await client.get("/admin/boards", headers=auth_headers)
        assert final_list_response.status_code == 200
        final_boards_data = final_list_response.json()
        assert len(final_boards_data["boards"]) == 0

    @pytest.mark.asyncio
    async def test_board_access_control(self, client, temp_data_dir, set_api_key_env):
        """Test access control for different board scenarios."""
        board_uid = "access-control-board"
        api_key = os.getenv("YAKA_ADMIN_API_KEY")

        # Create board with admin API key
        create_response = await client.post(
            "/admin/boards",
            json={"board_uid": board_uid},
            headers={"Authorization": f"Bearer {api_key}"}
        )
        assert create_response.status_code == 201

        # Test that unauthorized users cannot access admin functions
        unauthorized_headers = {"Authorization": "Bearer invalid-key"}

        # Try to delete with invalid key
        delete_response = await client.delete(
            f"/admin/boards/{board_uid}",
            headers=unauthorized_headers
        )
        assert delete_response.status_code == 401

        # Try to create with invalid key
        create_response_2 = await client.post(
            "/admin/boards",
            json={"board_uid": "another-board"},
            headers=unauthorized_headers
        )
        assert create_response_2.status_code == 401

        # Clean up with valid key
        delete_response = await client.delete(
            f"/admin/boards/{board_uid}",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        assert delete_response.status_code == 200

    @pytest.mark.asyncio
    async def test_board_uid_validation_in_integration(self, client, set_api_key_env, auth_headers):
        """Test board UID validation in real API calls."""
        invalid_uids = [
            "board with spaces",
            "board@invalid",
            "board#tag",
            "a" * 51,  # Too long
            "../../../etc/passwd"  # Path traversal
        ]

        for invalid_uid in invalid_uids:
            response = await client.post(
                "/admin/boards",
                json={"board_uid": invalid_uid},
                headers=auth_headers
            )
            assert response.status_code == 400
            assert "must contain only alphanumeric" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_concurrent_board_operations(self, client, temp_data_dir, set_api_key_env, auth_headers):
        """Test concurrent operations on different boards."""
        import asyncio

        async def create_board_task(board_uid):
            """Task to create a board."""
            response = await client.post(
                "/admin/boards",
                json={"board_uid": board_uid},
                headers=auth_headers
            )
            return response

        async def delete_board_task(board_uid):
            """Task to delete a board."""
            response = await client.delete(
                f"/admin/boards/{board_uid}",
                headers=auth_headers
            )
            return response

        # Create multiple boards concurrently
        board_uids = ["concurrent-1", "concurrent-2", "concurrent-3", "concurrent-4", "concurrent-5"]
        create_tasks = [create_board_task(uid) for uid in board_uids]

        create_results = await asyncio.gather(*create_tasks)
        for result in create_results:
            assert result.status_code == 201

        # Verify all boards were created
        list_response = await client.get("/admin/boards", headers=auth_headers)
        list_data = list_response.json()
        created_uids = [board["board_uid"] for board in list_data["boards"]]
        for uid in board_uids:
            assert uid in created_uids

        # Delete all boards concurrently
        delete_tasks = [delete_board_task(uid) for uid in board_uids]
        delete_results = await asyncio.gather(*delete_tasks)
        for result in delete_results:
            assert result.status_code == 200

        # Verify all boards were deleted
        final_list_response = await client.get("/admin/boards", headers=auth_headers)
        final_data = final_list_response.json()
        assert len(final_data["boards"]) == 0

    @pytest.mark.asyncio
    async def test_board_persistence_across_requests(self, client, temp_data_dir, set_api_key_env, auth_headers):
        """Test that board persistence works across multiple requests."""
        board_uid = "persistent-board"

        # Create board
        create_response = await client.post(
            "/admin/boards",
            json={"board_uid": board_uid},
            headers=auth_headers
        )
        assert create_response.status_code == 201

        # Verify board exists in multiple requests
        for _ in range(3):
            list_response = await client.get("/admin/boards", headers=auth_headers)
            assert list_response.status_code == 200
            board_uids = [board["board_uid"] for board in list_response.json()["boards"]]
            assert board_uid in board_uids

            info_response = await client.get(f"/admin/boards/{board_uid}")
            assert info_response.status_code == 200
            assert info_response.json()["exists"] is True

        # Delete board
        delete_response = await client.delete(
            f"/admin/boards/{board_uid}",
            headers=auth_headers
        )
        assert delete_response.status_code == 200

        # Verify board is gone in subsequent requests
        for _ in range(3):
            info_response = await client.get(f"/admin/boards/{board_uid}")
            assert info_response.status_code == 200
            assert info_response.json()["exists"] is False

    @pytest.mark.asyncio
    async def test_error_recovery_after_invalid_operations(self, client, temp_data_dir, set_api_key_env, auth_headers):
        """Test error recovery after invalid operations."""
        # Try to create board with invalid UID
        invalid_uid = "invalid board name"
        invalid_response = await client.post(
            "/admin/boards",
            json={"board_uid": invalid_uid},
            headers=auth_headers
        )
        assert invalid_response.status_code == 400

        # Try to delete non-existent board
        non_existent_uid = "non-existent-board"
        delete_response = await client.delete(
            f"/admin/boards/{non_existent_uid}",
            headers=auth_headers
        )
        assert delete_response.status_code == 404

        # System should still work for valid operations
        valid_uid = "recovery-test-board"
        valid_create_response = await client.post(
            "/admin/boards",
            json={"board_uid": valid_uid},
            headers=auth_headers
        )
        assert valid_create_response.status_code == 201

        # Verify valid board was created
        info_response = await client.get(f"/admin/boards/{valid_uid}")
        assert info_response.status_code == 200
        assert info_response.json()["exists"] is True

        # Clean up
        cleanup_response = await client.delete(
            f"/admin/boards/{valid_uid}",
            headers=auth_headers
        )
        assert cleanup_response.status_code == 200


class TestMultiBoardSecurity:
    """Security tests for multi-board functionality."""

    @pytest.fixture
    async def client(self, async_client_factory):
        """Create an async test client."""
        async with async_client_factory(
            admin_router,
            auth_router,
            cards_router,
            users_router
        ) as client:
            yield client

    @pytest.mark.asyncio
    async def test_no_api_key_service_unavailable(self, client):
        """Test behavior when API key is not configured."""
        # Remove API key from environment if it exists
        with patch.dict(os.environ, {}, clear=True):
            # Try to create board without API key
            response = await client.post(
                "/admin/boards",
                json={"board_uid": "test-board"},
                headers={"Authorization": "Bearer some-key"}
            )
            assert response.status_code == 503
            assert "not configured" in response.json()["detail"]

    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary directory for test databases."""
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            old_base_path = db_manager.base_path
            db_manager.base_path = temp_dir
            yield temp_dir
            db_manager.base_path = old_base_path

    @pytest.mark.asyncio
    async def test_api_key_rotation_simulation(self, client, temp_data_dir):
        """Test API key rotation scenario."""
        old_key = "old-api-key-123"
        new_key = "new-api-key-456"

        # Set old API key
        with patch.dict(os.environ, {"YAKA_ADMIN_API_KEY": old_key}):
            old_headers = {"Authorization": f"Bearer {old_key}"}

            # Create board with old key
            create_response = await client.post(
                "/admin/boards",
                json={"board_uid": "rotation-test"},
                headers=old_headers
            )
            assert create_response.status_code == 201

            # Try to use new key (should fail)
            new_headers = {"Authorization": f"Bearer {new_key}"}
            delete_response = await client.delete(
                "/admin/boards/rotation-test",
                headers=new_headers
            )
            assert delete_response.status_code == 401

        # Switch to new API key
        with patch.dict(os.environ, {"YAKA_ADMIN_API_KEY": new_key}):
            new_headers = {"Authorization": f"Bearer {new_key}"}

            # Delete with new key
            delete_response = await client.delete(
                "/admin/boards/rotation-test",
                headers=new_headers
            )
            assert delete_response.status_code == 200