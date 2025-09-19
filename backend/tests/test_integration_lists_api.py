"""Integration tests for the kanban lists router."""

import pytest
from app.routers.auth import router as auth_router
from app.routers.lists import router as lists_router


@pytest.mark.asyncio
async def test_admin_creates_lists_and_users_can_read(
    async_client_factory, seed_admin_user, create_regular_user, login_user
):
    seed_admin_user()
    create_regular_user("reader@example.com", "reader123", display_name="Reader")

    async with async_client_factory(auth_router, lists_router) as client:
        admin_token = await login_user(client, "admin@yaka.local", "Admin123")

        backlog_response = await client.post(
            "/lists/",
            json={"name": "Backlog", "order": 1},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert backlog_response.status_code == 200

        progress_response = await client.post(
            "/lists/",
            json={"name": "In Progress", "order": 2},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert progress_response.status_code == 200

        user_token = await login_user(client, "reader@example.com", "reader123")
        forbidden_response = await client.post(
            "/lists/",
            json={"name": "Should Fail", "order": 3},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert forbidden_response.status_code == 403

        lists_response = await client.get(
            "/lists/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert lists_response.status_code == 200
        lists_payload = lists_response.json()

    assert [lst["name"] for lst in lists_payload] == ["Backlog", "In Progress"]


@pytest.mark.asyncio
async def test_admin_can_update_and_delete_lists(async_client_factory, seed_admin_user, login_user):
    seed_admin_user()

    async with async_client_factory(auth_router, lists_router) as client:
        token = await login_user(client, "admin@yaka.local", "Admin123")

        backlog_response = await client.post(
            "/lists/",
            json={"name": "Backlog", "order": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert backlog_response.status_code == 200
        backlog_data = backlog_response.json()

        progress_response = await client.post(
            "/lists/",
            json={"name": "In Progress", "order": 2},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert progress_response.status_code == 200
        progress_data = progress_response.json()

        update_response = await client.put(
            f"/lists/{progress_data['id']}",
            json={"name": "Doing", "order": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Doing"

        delete_response = await client.request(
            "DELETE",
            f"/lists/{backlog_data['id']}",
            json={"target_list_id": progress_data["id"]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert delete_response.status_code == 200

        fetch_deleted = await client.get(
            f"/lists/{backlog_data['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fetch_deleted.status_code == 404

        cards_count = await client.get(
            f"/lists/{progress_data['id']}/cards-count",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert cards_count.status_code == 200
        assert cards_count.json()["list_name"] == "Doing"

        reorder_response = await client.post(
            "/lists/reorder",
            json={"list_orders": {progress_data["id"]: 1}},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert reorder_response.status_code == 200
