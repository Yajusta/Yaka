"""Integration tests for the card comments router."""

import pytest

from app.routers.auth import router as auth_router
from app.routers.cards import router as cards_router
from app.routers.card_comments import router as card_comments_router


@pytest.mark.asyncio
async def test_card_comments_crud(
    async_client_factory,
    seed_admin_user,
    create_regular_user,
    create_list_record,
    login_user,
):
    seed_admin_user()
    list_id = create_list_record("Backlog", 1)
    create_regular_user("commenter@example.com", "Comment123!", display_name="Commenter")

    async with async_client_factory(auth_router, cards_router, card_comments_router) as client:
        token = await login_user(client, "commenter@example.com", "Comment123!")

        card_response = await client.post(
            "/cards/",
            json={
                "title": "Comment Card",
                "description": "Track discussion",
                "list_id": list_id,
                "priority": "medium",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert card_response.status_code == 200
        card_id = card_response.json()["id"]

        create_comment_response = await client.post(
            "/card-comments/",
            json={"card_id": card_id, "comment": "First comment"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert create_comment_response.status_code == 200
        comment_payload = create_comment_response.json()
        comment_id = comment_payload["id"]
        assert comment_payload["comment"] == "First comment"

        list_response = await client.get(
            f"/card-comments/card/{card_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_response.status_code == 200
        assert any(comment["id"] == comment_id for comment in list_response.json())

        update_response = await client.put(
            f"/card-comments/{comment_id}",
            json={"comment": "Updated comment"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["comment"] == "Updated comment"

        delete_response = await client.delete(
            f"/card-comments/{comment_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert delete_response.status_code == 200

        after_delete = await client.get(
            f"/card-comments/card/{card_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert after_delete.status_code == 200
        assert after_delete.json() == []
