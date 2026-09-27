"""Integration tests for the card history endpoints of the cards router."""

import pytest
from app.routers.auth import router as auth_router
from app.routers.cards import router as cards_router


@pytest.mark.asyncio
async def test_card_history_endpoints(
    async_client_factory,
    seed_admin_user,
    create_list_record,
    login_user,
):
    seed_admin_user()
    list_id = create_list_record("Backlog", 1)

    async with async_client_factory(auth_router, cards_router) as client:
        token = await login_user(client, "admin@yaka.local", "Admin-Test1")

        me_response = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_response.status_code == 200
        user_id = me_response.json()["id"]

        card_response = await client.post(
            "/cards/",
            json={
                "title": "History Card",
                "description": "Track history",
                "list_id": list_id,
                "priority": "medium",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert card_response.status_code == 200
        card_id = card_response.json()["id"]

        history_payload = {
            "action": "custom",
            "description": "Manual entry",
        }
        create_history_response = await client.post(
            f"/cards/{card_id}/history",
            json=history_payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert create_history_response.status_code == 200
        created_entry = create_history_response.json()
        assert created_entry["action"] == "custom"
        assert created_entry["description"] == "Manual entry"
        assert created_entry["card_id"] == card_id
        assert created_entry["user_id"] == user_id

        list_history_response = await client.get(
            f"/cards/{card_id}/history",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_history_response.status_code == 200
        history_entries = list_history_response.json()
        assert len(history_entries) >= 1
        assert history_entries[0]["card_id"] == card_id

        missing_history_response = await client.get(
            f"/cards/{card_id + 999}/history",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert missing_history_response.status_code == 404

        invalid_create_response = await client.post(
            f"/cards/{card_id + 999}/history",
            json={"action": "custom", "description": "Invalid"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert invalid_create_response.status_code == 404
