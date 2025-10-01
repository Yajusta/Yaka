"""Integration tests for the labels router."""

import pytest
from app.routers.auth import router as auth_router
from app.routers.cards import router as cards_router
from app.routers.labels import router as labels_router


@pytest.mark.asyncio
async def test_label_crud_permissions(async_client_factory, seed_admin_user, create_regular_user, login_user):
    seed_admin_user()
    create_regular_user("labeluser@example.com", "Label123", display_name="Label User")

    async with async_client_factory(auth_router, labels_router) as client:
        admin_token = await login_user(client, "admin@yaka.local", "Admin123")
        create_response = await client.post(
            "/labels/",
            json={"name": "Urgent", "color": "#ff0000"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert create_response.status_code == 200
        label_payload = create_response.json()
        assert label_payload["name"] == "Urgent"

        duplicate_response = await client.post(
            "/labels/",
            json={"name": "Urgent", "color": "#00ff00"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert duplicate_response.status_code == 400

        user_token = await login_user(client, "labeluser@example.com", "Label123")
        forbidden_response = await client.post(
            "/labels/",
            json={"name": "ShouldFail", "color": "#123456"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert forbidden_response.status_code == 403

        list_response = await client.get(
            "/labels/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert list_response.status_code == 200
        assert any(label["name"] == "Urgent" for label in list_response.json())

        update_response = await client.put(
            f"/labels/{label_payload['id']}",
            json={"name": "Important", "color": "#ffaa00"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Important"

        delete_response = await client.delete(
            f"/labels/{label_payload['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert delete_response.status_code == 200

        fetch_deleted = await client.get(
            f"/labels/{label_payload['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert fetch_deleted.status_code == 404


@pytest.mark.asyncio
async def test_label_deletion_detaches_from_cards(
    async_client_factory,
    seed_admin_user,
    create_regular_user,
    create_list_record,
    login_user,
):
    seed_admin_user()
    list_id = create_list_record("Backlog", 1)
    create_regular_user("labelowner@example.com", "LabelOwner123!", display_name="Owner")

    async with async_client_factory(auth_router, labels_router, cards_router) as client:
        admin_token = await login_user(client, "admin@yaka.local", "Admin123")
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        label_response = await client.post(
            "/labels/",
            json={"name": "TempLabel", "color": "#00ffcc"},
            headers=admin_headers,
        )
        assert label_response.status_code == 200
        label_id = label_response.json()["id"]

        owner_token = await login_user(client, "labelowner@example.com", "LabelOwner123!")
        owner_headers = {"Authorization": f"Bearer {owner_token}"}

        card_response = await client.post(
            "/cards/",
            json={
                "title": "Card With Label",
                "description": "Should lose label on delete",
                "list_id": list_id,
                "priority": "medium",
                "label_ids": [label_id],
            },
            headers=owner_headers,
        )
        assert card_response.status_code == 200
        card_payload = card_response.json()
        card_id = card_payload["id"]
        assert [label["id"] for label in card_payload["labels"]] == [label_id]

        delete_response = await client.delete(
            f"/labels/{label_id}",
            headers=admin_headers,
        )
        assert delete_response.status_code == 200

        card_after_delete = await client.get(
            f"/cards/{card_id}",
            headers=owner_headers,
        )
        assert card_after_delete.status_code == 200
        assert card_after_delete.json()["labels"] == []

        label_fetch = await client.get(
            f"/labels/{label_id}",
            headers=admin_headers,
        )
        assert label_fetch.status_code == 404
