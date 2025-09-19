"""Integration tests for the cards router."""

import pytest

from app.routers.auth import router as auth_router
from app.routers.cards import router as cards_router
from app.routers.labels import router as labels_router

@pytest.mark.asyncio
async def test_card_lifecycle(
    async_client_factory,
    seed_admin_user,
    create_regular_user,
    create_list_record,
    login_user,
):
    seed_admin_user()
    list_id = create_list_record("Backlog", 1)
    target_list_id = create_list_record("Done", 2)
    create_regular_user("writer@example.com", "UserPass123!", display_name="Writer")

    async with async_client_factory(auth_router, cards_router) as client:
        token = await login_user(client, "writer@example.com", "UserPass123!")

        create_response = await client.post(
            "/cards/",
            json={
                "titre": "Sample Card",
                "description": "Created via API",
                "list_id": list_id,
                "priorite": "medium",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert create_response.status_code == 200
        card_payload = create_response.json()
        card_id = card_payload["id"]
        assert card_payload["list_id"] == list_id

        list_response = await client.get(
            "/cards/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_response.status_code == 200
        assert any(card["id"] == card_id for card in list_response.json())

        detail_response = await client.get(
            f"/cards/{card_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert detail_response.status_code == 200
        assert detail_response.json()["titre"] == "Sample Card"

        update_response = await client.put(
            f"/cards/{card_id}",
            json={"description": "Updated description"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["description"] == "Updated description"

        move_response = await client.patch(
            f"/cards/{card_id}/list",
            json={"list_id": target_list_id},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert move_response.status_code == 200
        assert move_response.json()["list_id"] == target_list_id

        moved_cards = await client.get(
            "/cards/",
            params={"list_id": target_list_id},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert moved_cards.status_code == 200
        assert any(card["id"] == card_id for card in moved_cards.json())

        archive_response = await client.patch(
            f"/cards/{card_id}/archive",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert archive_response.status_code == 200
        assert archive_response.json()["is_archived"] is True

        unarchive_response = await client.patch(
            f"/cards/{card_id}/unarchive",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert unarchive_response.status_code == 200
        assert unarchive_response.json()["is_archived"] is False

        delete_response = await client.delete(
            f"/cards/{card_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert delete_response.status_code == 200

        missing_response = await client.get(
            f"/cards/{card_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert missing_response.status_code == 404

        final_list = await client.get(
            "/cards/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert final_list.status_code == 200
        assert all(card["id"] != card_id for card in final_list.json())


@pytest.mark.asyncio
async def test_card_filters_bulk_move_and_archive(
    async_client_factory,
    seed_admin_user,
    create_regular_user,
    create_list_record,
    login_user,
):
    seed_admin_user()
    list_a = create_list_record("Backlog", 1)
    list_b = create_list_record("Review", 2)
    create_regular_user("bulk@example.com", "Bulk123!", display_name="Bulk User")
    create_regular_user("assignee@example.com", "Assign123!", display_name="Assignee")

    async with async_client_factory(auth_router, labels_router, cards_router) as client:
        admin_token = await login_user(client, "admin@yaka.local", "admin123")
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        label_response = await client.post(
            "/labels/",
            json={"nom": "Prioritaire", "couleur": "#ff8800"},
            headers=admin_headers,
        )
        assert label_response.status_code == 200
        label_id = label_response.json()["id"]

        user_token = await login_user(client, "bulk@example.com", "Bulk123!")
        user_headers = {"Authorization": f"Bearer {user_token}"}
        user_me = await client.get("/auth/me", headers=user_headers)
        assert user_me.status_code == 200
        creator_id = user_me.json()["id"]

        assignee_token = await login_user(client, "assignee@example.com", "Assign123!")
        assignee_headers = {"Authorization": f"Bearer {assignee_token}"}
        assignee_me = await client.get("/auth/me", headers=assignee_headers)
        assert assignee_me.status_code == 200
        assignee_id = assignee_me.json()["id"]

        card_alpha = await client.post(
            "/cards/",
            json={
                "titre": "Alpha Task",
                "description": "Needs review",
                "list_id": list_a,
                "priorite": "medium",
                "label_ids": [label_id],
                "assignee_id": assignee_id,
            },
            headers=user_headers,
        )
        assert card_alpha.status_code == 200
        card_alpha_payload = card_alpha.json()
        card_alpha_id = card_alpha_payload["id"]

        card_beta = await client.post(
            "/cards/",
            json={
                "titre": "Beta Task",
                "description": "Contains beta keyword",
                "list_id": list_a,
                "priorite": "low",
            },
            headers=user_headers,
        )
        assert card_beta.status_code == 200
        card_beta_payload = card_beta.json()
        card_beta_id = card_beta_payload["id"]

        label_filter = await client.get(
            "/cards/",
            params={"label_id": label_id},
            headers=user_headers,
        )
        assert label_filter.status_code == 200
        label_ids = [card["id"] for card in label_filter.json()]
        assert label_ids == [card_alpha_id]

        search_filter = await client.get(
            "/cards/",
            params={"search": "Beta"},
            headers=user_headers,
        )
        assert search_filter.status_code == 200
        assert any(card["id"] == card_beta_id for card in search_filter.json())

        assignee_filter = await client.get(
            "/cards/",
            params={"assignee_id": assignee_id},
            headers=user_headers,
        )
        assert assignee_filter.status_code == 200
        assignee_matches = [card["id"] for card in assignee_filter.json()]
        assert assignee_matches == [card_alpha_id]

        move_same_list = await client.patch(
            f"/cards/{card_beta_id}/move",
            json={"source_list_id": list_a, "target_list_id": list_a, "position": 0},
            headers=user_headers,
        )
        assert move_same_list.status_code == 200

        bulk_move = await client.post(
            "/cards/bulk-move",
            json={"card_ids": [card_alpha_id, card_beta_id], "target_list_id": list_b},
            headers=user_headers,
        )
        assert bulk_move.status_code == 200
        moved_cards = bulk_move.json()
        assert {card["id"] for card in moved_cards} == {card_alpha_id, card_beta_id}
        assert all(card["list_id"] == list_b for card in moved_cards)

        list_b_cards = await client.get(
            "/cards/",
            params={"list_id": list_b},
            headers=user_headers,
        )
        assert list_b_cards.status_code == 200
        list_b_ids = {card["id"] for card in list_b_cards.json()}
        assert {card_alpha_id, card_beta_id}.issubset(list_b_ids)

        archive_beta = await client.patch(
            f"/cards/{card_beta_id}/archive",
            headers=user_headers,
        )
        assert archive_beta.status_code == 200
        assert archive_beta.json()["is_archived"] is True

        active_cards = await client.get(
            "/cards/",
            params={"list_id": list_b},
            headers=user_headers,
        )
        assert active_cards.status_code == 200
        assert all(card["id"] != card_beta_id for card in active_cards.json())

        archived_cards = await client.get(
            "/cards/archived",
            headers=user_headers,
        )
        assert archived_cards.status_code == 200
        assert any(card["id"] == card_beta_id for card in archived_cards.json())

        include_archived = await client.get(
            "/cards/",
            params={"include_archived": "true"},
            headers=user_headers,
        )
        assert include_archived.status_code == 200
        assert any(card["id"] == card_beta_id for card in include_archived.json())

        invalid_statut = await client.get(
            "/cards/",
            params={"statut": "unknown"},
            headers=user_headers,
        )
        assert invalid_statut.status_code == 400





@pytest.mark.asyncio
async def test_legacy_statut_endpoint(
    async_client_factory,
    seed_admin_user,
    create_regular_user,
    create_list_record,
    login_user,
):
    seed_admin_user()
    list_a = create_list_record("A faire", 1)
    list_b = create_list_record("En cours", 2)
    list_c = create_list_record("Termin?", 3)
    create_regular_user("legacy@example.com", "Legacy123!", display_name="Legacy")

    async with async_client_factory(auth_router, cards_router) as client:
        token = await login_user(client, "legacy@example.com", "Legacy123!")
        headers = {"Authorization": f"Bearer {token}"}

        create_response = await client.post(
            "/cards/",
            json={
                "titre": "Legacy Card",
                "description": "Will move via status endpoint",
                "list_id": list_a,
                "priorite": "medium",
            },
            headers=headers,
        )
        assert create_response.status_code == 200
        card_id = create_response.json()["id"]

        move_en_cours = await client.patch(
            f"/cards/{card_id}/statut",
            params={"statut": "en_cours"},
            headers=headers,
        )
        assert move_en_cours.status_code == 200
        assert move_en_cours.json()["list_id"] == list_b

        move_termine = await client.patch(
            f"/cards/{card_id}/statut",
            params={"statut": "termine"},
            headers=headers,
        )
        assert move_termine.status_code == 200
        assert move_termine.json()["list_id"] == list_c

        invalid_response = await client.patch(
            f"/cards/{card_id}/statut",
            params={"statut": "unknown"},
            headers=headers,
        )
        assert invalid_response.status_code == 400

        missing_response = await client.patch(
            "/cards/99999/statut",
            params={"statut": "en_cours"},
            headers=headers,
        )
        assert missing_response.status_code == 404


@pytest.mark.asyncio
async def test_card_update_assigns_and_labels(
    async_client_factory,
    seed_admin_user,
    create_regular_user,
    create_list_record,
    login_user,
):
    seed_admin_user()
    list_id = create_list_record("Backlog", 1)
    create_regular_user("cardowner@example.com", "Owner123!", display_name="Owner")
    create_regular_user("teammate@example.com", "Mate123!", display_name="Teammate")

    async with async_client_factory(auth_router, labels_router, cards_router) as client:
        admin_token = await login_user(client, "admin@yaka.local", "admin123")
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        label_response = await client.post(
            "/labels/",
            json={"nom": "Bug", "couleur": "#ff0000"},
            headers=admin_headers,
        )
        assert label_response.status_code == 200
        label_id = label_response.json()["id"]

        owner_token = await login_user(client, "cardowner@example.com", "Owner123!")
        owner_headers = {"Authorization": f"Bearer {owner_token}"}

        teammate_token = await login_user(client, "teammate@example.com", "Mate123!")
        teammate_headers = {"Authorization": f"Bearer {teammate_token}"}
        teammate_info = await client.get("/auth/me", headers=teammate_headers)
        assert teammate_info.status_code == 200
        teammate_id = teammate_info.json()["id"]

        create_response = await client.post(
            "/cards/",
            json={
                "titre": "Assignment Card",
                "description": "Needs labels and assignee",
                "list_id": list_id,
                "priorite": "medium",
            },
            headers=owner_headers,
        )
        assert create_response.status_code == 200
        card_payload = create_response.json()
        card_id = card_payload["id"]
        assert card_payload["labels"] == []
        assert card_payload["assignee"] is None

        update_response = await client.put(
            f"/cards/{card_id}",
            json={"label_ids": [label_id], "assignee_id": teammate_id},
            headers=owner_headers,
        )
        assert update_response.status_code == 200
        updated_card = update_response.json()
        assert [label["id"] for label in updated_card["labels"]] == [label_id]
        assert updated_card["assignee"]["id"] == teammate_id

        clear_response = await client.put(
            f"/cards/{card_id}",
            json={"label_ids": [], "assignee_id": None},
            headers=owner_headers,
        )
        assert clear_response.status_code == 200
        cleared_card = clear_response.json()
        assert cleared_card["labels"] == []
        assert cleared_card["assignee"] is None
        history_response = await client.get(
            f"/cards/{card_id}/history",
            headers=owner_headers,
        )
        assert history_response.status_code == 200
        history_entries = history_response.json()
        actions = {entry["action"] for entry in history_entries}
        assert "create" in actions
        assert "assignee_change" in actions
        descriptions = [entry["description"] for entry in history_entries if entry["action"] == "assignee_change"]
        assert any("Teammate" in desc or "personne" in desc for desc in descriptions)

        assert cleared_card["assignee"] is None
