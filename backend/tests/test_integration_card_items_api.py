"""Integration tests for the card items router."""

import pytest

from app.routers.auth import router as auth_router
from app.routers.cards import router as cards_router
from app.routers.card_items import router as card_items_router


@pytest.mark.asyncio
async def test_card_items_crud(
    async_client_factory,
    seed_admin_user,
    create_regular_user,
    create_list_record,
    login_user,
):
    seed_admin_user()
    list_id = create_list_record("Backlog", 1)
    create_regular_user("items@example.com", "Items123!", display_name="Items User")

    async with async_client_factory(auth_router, cards_router, card_items_router) as client:
        token = await login_user(client, "items@example.com", "Items123!")

        # Get user ID
        me_response = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_response.status_code == 200
        user_id = me_response.json()["id"]

        card_response = await client.post(
            "/cards/",
            json={
                "title": "Checklist Card",
                "description": "Needs tasks",
                "list_id": list_id,
                "priority": "medium",
                "assignee_id": user_id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert card_response.status_code == 200
        card_id = card_response.json()["id"]

        create_item_response = await client.post(
            "/card-items/",
            json={"card_id": card_id, "text": "First task", "is_done": False},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert create_item_response.status_code == 200
        item_payload = create_item_response.json()
        item_id = item_payload["id"]
        assert item_payload["text"] == "First task"

        list_response = await client.get(
            f"/card-items/card/{card_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1

        update_response = await client.put(
            f"/card-items/{item_id}",
            json={"is_done": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["is_done"] is True

        delete_response = await client.delete(
            f"/card-items/{item_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert delete_response.status_code == 200

        after_delete = await client.get(
            f"/card-items/card/{card_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert after_delete.status_code == 200
        assert after_delete.json() == []
