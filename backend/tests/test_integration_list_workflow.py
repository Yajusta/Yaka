"""Integration tests for complete list management workflow."""

import pytest
import sys
import os
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from httpx import AsyncClient, ASGITransport
    from asgi_lifespan import LifespanManager
except Exception:
    pytest.skip("httpx or asgi_lifespan not installed in test environment", allow_module_level=True)

from app.main import app
from app.database import SessionLocal
from app.models.kanban_list import KanbanList
from app.models.card import Card
from app.models.user import User
from app.services.user import get_user_by_email


@pytest.fixture
async def client():
    """Fixture pour créer un client de test."""
    transport = ASGITransport(app=app)
    async with LifespanManager(app):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.fixture
def db_session():
    """Fixture pour créer une session de base de données de test."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
async def admin_headers(client):
    """Fixture pour obtenir les headers d'authentification admin."""
    resp_login = await client.post("/auth/login", data={"username": "admin@yaka.local", "password": "admin123"})
    assert resp_login.status_code == 200
    token = resp_login.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def user_headers(client, db_session):
    """Fixture pour obtenir les headers d'authentification utilisateur normal."""
    test_user_email = "testuser@example.com"

    # Nettoyer l'utilisateur existant s'il existe
    existing_user = get_user_by_email(db_session, test_user_email)
    if existing_user:
        db_session.delete(existing_user)
        db_session.commit()

    # Créer un nouvel utilisateur via l'API d'invitation
    admin_resp = await client.post("/auth/login", data={"username": "admin@yaka.local", "password": "admin123"})
    admin_token = admin_resp.json().get("access_token")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Inviter l'utilisateur
    with patch("app.services.email.send_invitation") as mock_send:
        invite_resp = await client.post(
            "/users/invite",
            json={"email": test_user_email, "display_name": "Test User", "role": "user"},
            headers=admin_headers,
        )
        assert invite_resp.status_code == 200

        # Récupérer le token d'invitation
        token = mock_send.call_args[1]["token"]

    # Définir le mot de passe
    password_resp = await client.post("/users/set-password", json={"token": token, "password": "testpass123"})
    assert password_resp.status_code == 200

    # Se connecter avec l'utilisateur
    login_resp = await client.post("/auth/login", data={"username": test_user_email, "password": "testpass123"})
    assert login_resp.status_code == 200
    user_token = login_resp.json().get("access_token")

    yield {"Authorization": f"Bearer {user_token}"}

    # Nettoyer après le test
    user = get_user_by_email(db_session, test_user_email)
    if user:
        db_session.delete(user)
        db_session.commit()


def clean_database(db_session):
    """Nettoie la base de données pour les tests."""
    # Supprimer les cartes en premier (contrainte de clé étrangère)
    db_session.query(Card).delete()
    db_session.query(KanbanList).delete()
    db_session.commit()


class TestListManagementIntegration:
    """Tests d'intégration pour la gestion complète des listes."""

    @pytest.mark.asyncio
    async def test_complete_list_lifecycle(self, client, admin_headers, db_session):
        """Test du cycle de vie complet d'une liste: création, modification, suppression."""
        # Arrange - Nettoyer la base de données
        clean_database(db_session)

        # Act & Assert - Créer une liste
        create_response = await client.post(
            "/lists/", json={"name": "Nouvelle Liste", "order": 1}, headers=admin_headers
        )

        assert create_response.status_code == 200
        created_list = create_response.json()
        assert created_list["name"] == "Nouvelle Liste"
        assert created_list["order"] == 1
        list_id = created_list["id"]

        # Vérifier que la liste existe dans la base de données
        db_list = db_session.query(KanbanList).filter(KanbanList.id == list_id).first()
        assert db_list is not None
        assert db_list.name == "Nouvelle Liste"

        # Modifier la liste
        update_response = await client.put(
            f"/lists/{list_id}", json={"name": "Liste Modifiée", "order": 2}, headers=admin_headers
        )

        assert update_response.status_code == 200
        updated_list = update_response.json()
        assert updated_list["name"] == "Liste Modifiée"
        assert updated_list["order"] == 2

        # Vérifier la modification dans la base de données
        db_session.refresh(db_list)
        assert db_list.name == "Liste Modifiée"
        assert db_list.order == 2

        # Créer une deuxième liste pour pouvoir supprimer la première
        second_list_response = await client.post(
            "/lists/", json={"name": "Liste de Destination", "order": 3}, headers=admin_headers
        )
        assert second_list_response.status_code == 200
        second_list_id = second_list_response.json()["id"]

        # Supprimer la première liste
        delete_response = await client.delete(
            f"/lists/{list_id}", json={"target_list_id": second_list_id}, headers=admin_headers
        )

        assert delete_response.status_code == 200

        # Vérifier que la liste a été supprimée
        deleted_list = db_session.query(KanbanList).filter(KanbanList.id == list_id).first()
        assert deleted_list is None

        # Vérifier que la deuxième liste existe toujours
        remaining_list = db_session.query(KanbanList).filter(KanbanList.id == second_list_id).first()
        assert remaining_list is not None

    @pytest.mark.asyncio
    async def test_card_movement_between_dynamic_lists(self, client, admin_headers, user_headers, db_session):
        """Test du déplacement de cartes entre des listes dynamiques."""
        # Arrange - Nettoyer et créer des listes
        clean_database(db_session)

        # Créer trois listes
        lists_data = [
            {"name": "Backlog", "order": 1},
            {"name": "En Développement", "order": 2},
            {"name": "Tests", "order": 3},
        ]

        created_lists = []
        for list_data in lists_data:
            response = await client.post("/lists/", json=list_data, headers=admin_headers)
            assert response.status_code == 200
            created_lists.append(response.json())

        # Créer des cartes dans la première liste
        cards_data = [
            {
                "titre": "Tâche 1",
                "description": "Description 1",
                "list_id": created_lists[0]["id"],
                "priorite": "haute",
            },
            {
                "titre": "Tâche 2",
                "description": "Description 2",
                "list_id": created_lists[0]["id"],
                "priorite": "moyenne",
            },
        ]

        created_cards = []
        for card_data in cards_data:
            response = await client.post("/cards/", json=card_data, headers=user_headers)
            assert response.status_code == 200
            created_cards.append(response.json())

        # Vérifier que les cartes sont dans la première liste
        for card in created_cards:
            assert card["list_id"] == created_lists[0]["id"]

        # Déplacer la première carte vers la deuxième liste
        move_response = await client.put(
            f"/cards/{created_cards[0]['id']}/move",
            json={"list_id": created_lists[1]["id"], "position": 0},
            headers=user_headers,
        )

        assert move_response.status_code == 200
        moved_card = move_response.json()
        assert moved_card["list_id"] == created_lists[1]["id"]

        # Vérifier dans la base de données
        db_card = db_session.query(Card).filter(Card.id == created_cards[0]["id"]).first()
        assert db_card.list_id == created_lists[1]["id"]

        # Déplacer la deuxième carte vers la troisième liste
        move_response2 = await client.put(
            f"/cards/{created_cards[1]['id']}/move",
            json={"list_id": created_lists[2]["id"], "position": 0},
            headers=user_headers,
        )

        assert move_response2.status_code == 200
        moved_card2 = move_response2.json()
        assert moved_card2["list_id"] == created_lists[2]["id"]

        # Vérifier la distribution finale des cartes
        final_cards = await client.get("/cards/", headers=user_headers)
        assert final_cards.status_code == 200
        cards_by_list = {}
        for card in final_cards.json():
            list_id = card["list_id"]
            if list_id not in cards_by_list:
                cards_by_list[list_id] = []
            cards_by_list[list_id].append(card)

        # Première liste: vide
        assert created_lists[0]["id"] not in cards_by_list or len(cards_by_list[created_lists[0]["id"]]) == 0
        # Deuxième liste: 1 carte
        assert len(cards_by_list[created_lists[1]["id"]]) == 1
        # Troisième liste: 1 carte
        assert len(cards_by_list[created_lists[2]["id"]]) == 1

    @pytest.mark.asyncio
    async def test_list_deletion_with_card_migration(self, client, admin_headers, user_headers, db_session):
        """Test de suppression de liste avec migration des cartes."""
        # Arrange - Nettoyer et créer des listes
        clean_database(db_session)

        # Créer deux listes
        source_list_response = await client.post(
            "/lists/", json={"name": "Liste à Supprimer", "order": 1}, headers=admin_headers
        )
        assert source_list_response.status_code == 200
        source_list = source_list_response.json()

        target_list_response = await client.post(
            "/lists/", json={"name": "Liste de Destination", "order": 2}, headers=admin_headers
        )
        assert target_list_response.status_code == 200
        target_list = target_list_response.json()

        # Créer des cartes dans la liste source
        cards_in_source = []
        for i in range(3):
            card_response = await client.post(
                "/cards/",
                json={
                    "titre": f"Carte {i+1}",
                    "description": f"Description {i+1}",
                    "list_id": source_list["id"],
                    "priorite": "moyenne",
                },
                headers=user_headers,
            )
            assert card_response.status_code == 200
            cards_in_source.append(card_response.json())

        # Vérifier le nombre de cartes avant suppression
        count_response = await client.get(f"/lists/{source_list['id']}/cards-count", headers=admin_headers)
        assert count_response.status_code == 200
        assert count_response.json()["count"] == 3

        # Supprimer la liste source avec migration vers la liste cible
        delete_response = await client.delete(
            f"/lists/{source_list['id']}", json={"target_list_id": target_list["id"]}, headers=admin_headers
        )

        assert delete_response.status_code == 200

        # Vérifier que la liste source a été supprimée
        get_source_response = await client.get(f"/lists/{source_list['id']}", headers=admin_headers)
        assert get_source_response.status_code == 404

        # Vérifier que toutes les cartes ont été migrées vers la liste cible
        target_count_response = await client.get(f"/lists/{target_list['id']}/cards-count", headers=admin_headers)
        assert target_count_response.status_code == 200
        assert target_count_response.json()["count"] == 3

        # Vérifier dans la base de données que les cartes ont bien été migrées
        migrated_cards = db_session.query(Card).filter(Card.list_id == target_list["id"]).all()
        assert len(migrated_cards) == 3

        # Vérifier que les IDs des cartes correspondent
        migrated_card_ids = {card.id for card in migrated_cards}
        original_card_ids = {card["id"] for card in cards_in_source}
        assert migrated_card_ids == original_card_ids

    @pytest.mark.asyncio
    async def test_list_reordering_workflow(self, client, admin_headers, db_session):
        """Test du workflow de réorganisation des listes."""
        # Arrange - Nettoyer et créer plusieurs listes
        clean_database(db_session)

        # Créer 4 listes avec des ordres séquentiels
        lists_data = [
            {"name": "Liste A", "order": 1},
            {"name": "Liste B", "order": 2},
            {"name": "Liste C", "order": 3},
            {"name": "Liste D", "order": 4},
        ]

        created_lists = []
        for list_data in lists_data:
            response = await client.post("/lists/", json=list_data, headers=admin_headers)
            assert response.status_code == 200
            created_lists.append(response.json())

        # Vérifier l'ordre initial
        get_lists_response = await client.get("/lists/", headers=admin_headers)
        assert get_lists_response.status_code == 200
        initial_lists = get_lists_response.json()

        assert len(initial_lists) == 4
        for i, lst in enumerate(initial_lists):
            assert lst["order"] == i + 1

        # Réorganiser les listes: inverser l'ordre
        new_orders = {
            created_lists[0]["id"]: 4,  # A: 1 -> 4
            created_lists[1]["id"]: 3,  # B: 2 -> 3
            created_lists[2]["id"]: 2,  # C: 3 -> 2
            created_lists[3]["id"]: 1,  # D: 4 -> 1
        }

        reorder_response = await client.post("/lists/reorder", json=new_orders, headers=admin_headers)
        assert reorder_response.status_code == 200

        # Vérifier le nouvel ordre
        get_reordered_response = await client.get("/lists/", headers=admin_headers)
        assert get_reordered_response.status_code == 200
        reordered_lists = get_reordered_response.json()

        # Les listes doivent être dans l'ordre: D, C, B, A
        expected_names = ["Liste D", "Liste C", "Liste B", "Liste A"]
        actual_names = [lst["name"] for lst in reordered_lists]
        assert actual_names == expected_names

        # Vérifier les ordres dans la base de données
        for lst in reordered_lists:
            db_list = db_session.query(KanbanList).filter(KanbanList.id == lst["id"]).first()
            assert db_list.order == lst["order"]

    @pytest.mark.asyncio
    async def test_permission_enforcement_workflow(self, client, admin_headers, user_headers, db_session):
        """Test de l'application des permissions dans le workflow complet."""
        # Arrange - Nettoyer et créer une liste
        clean_database(db_session)

        # Admin crée une liste
        create_response = await client.post(
            "/lists/", json={"name": "Liste Test Permissions", "order": 1}, headers=admin_headers
        )
        assert create_response.status_code == 200
        created_list = create_response.json()

        # User peut lire les listes
        read_response = await client.get("/lists/", headers=user_headers)
        assert read_response.status_code == 200
        lists = read_response.json()
        assert len(lists) == 1
        assert lists[0]["name"] == "Liste Test Permissions"

        # User ne peut pas créer de liste
        user_create_response = await client.post(
            "/lists/", json={"name": "Liste Interdite", "order": 2}, headers=user_headers
        )
        assert user_create_response.status_code == 403

        # User ne peut pas modifier de liste
        user_update_response = await client.put(
            f"/lists/{created_list['id']}", json={"name": "Modification Interdite"}, headers=user_headers
        )
        assert user_update_response.status_code == 403

        # User ne peut pas supprimer de liste
        user_delete_response = await client.delete(
            f"/lists/{created_list['id']}", json={"target_list_id": created_list["id"]}, headers=user_headers
        )
        assert user_delete_response.status_code == 403

        # User ne peut pas réorganiser les listes
        user_reorder_response = await client.post("/lists/reorder", json={created_list["id"]: 2}, headers=user_headers)
        assert user_reorder_response.status_code == 403

        # Admin peut toujours effectuer toutes les opérations
        admin_update_response = await client.put(
            f"/lists/{created_list['id']}", json={"name": "Modification Autorisée"}, headers=admin_headers
        )
        assert admin_update_response.status_code == 200

    @pytest.mark.asyncio
    async def test_data_integrity_during_operations(self, client, admin_headers, user_headers, db_session):
        """Test de l'intégrité des données pendant les opérations complexes."""
        # Arrange - Nettoyer et créer un environnement complexe
        clean_database(db_session)

        # Créer plusieurs listes
        lists = []
        for i in range(3):
            response = await client.post(
                "/lists/", json={"name": f"Liste {i+1}", "order": i + 1}, headers=admin_headers
            )
            assert response.status_code == 200
            lists.append(response.json())

        # Créer des cartes dans chaque liste
        all_cards = []
        for i, lst in enumerate(lists):
            for j in range(2):  # 2 cartes par liste
                card_response = await client.post(
                    "/cards/",
                    json={
                        "titre": f"Carte {i+1}-{j+1}",
                        "description": f"Description {i+1}-{j+1}",
                        "list_id": lst["id"],
                        "priorite": "moyenne",
                    },
                    headers=user_headers,
                )
                assert card_response.status_code == 200
                all_cards.append(card_response.json())

        # Vérifier l'état initial
        initial_card_count = len(all_cards)
        assert initial_card_count == 6  # 3 listes × 2 cartes

        # Effectuer des opérations complexes

        # 1. Déplacer des cartes entre listes
        move_response = await client.put(
            f"/cards/{all_cards[0]['id']}/move", json={"list_id": lists[1]["id"], "position": 0}, headers=user_headers
        )
        assert move_response.status_code == 200

        # 2. Supprimer une liste avec migration des cartes
        delete_response = await client.delete(
            f"/lists/{lists[2]['id']}", json={"target_list_id": lists[0]["id"]}, headers=admin_headers
        )
        assert delete_response.status_code == 200

        # 3. Vérifier l'intégrité des données

        # Vérifier que le nombre total de cartes est conservé
        final_cards_response = await client.get("/cards/", headers=user_headers)
        assert final_cards_response.status_code == 200
        final_cards = final_cards_response.json()
        assert len(final_cards) == initial_card_count

        # Vérifier qu'il ne reste que 2 listes
        final_lists_response = await client.get("/lists/", headers=admin_headers)
        assert final_lists_response.status_code == 200
        final_lists = final_lists_response.json()
        assert len(final_lists) == 2

        # Vérifier que toutes les cartes sont assignées à des listes existantes
        existing_list_ids = {lst["id"] for lst in final_lists}
        for card in final_cards:
            assert card["list_id"] in existing_list_ids

        # Vérifier dans la base de données
        db_cards = db_session.query(Card).all()
        db_lists = db_session.query(KanbanList).all()

        assert len(db_cards) == initial_card_count
        assert len(db_lists) == 2

        # Vérifier les contraintes de clé étrangère
        db_list_ids = {lst.id for lst in db_lists}
        for card in db_cards:
            assert card.list_id in db_list_ids

    @pytest.mark.asyncio
    async def test_migration_process_simulation(self, client, admin_headers, user_headers, db_session):
        """Test simulant le processus de migration depuis l'ancien système."""
        # Arrange - Simuler l'état initial avec les listes par défaut
        clean_database(db_session)

        # Créer les listes par défaut comme dans la migration
        default_lists_data = [
            {"name": "A faire", "order": 1},
            {"name": "En cours", "order": 2},
            {"name": "Terminé", "order": 3},
        ]

        default_lists = []
        for list_data in default_lists_data:
            response = await client.post("/lists/", json=list_data, headers=admin_headers)
            assert response.status_code == 200
            default_lists.append(response.json())

        # Créer des cartes comme si elles venaient de l'ancien système
        legacy_cards = [
            {"titre": "Ancienne tâche 1", "list_id": default_lists[0]["id"], "priorite": "haute"},
            {"titre": "Ancienne tâche 2", "list_id": default_lists[1]["id"], "priorite": "moyenne"},
            {"titre": "Ancienne tâche 3", "list_id": default_lists[2]["id"], "priorite": "basse"},
        ]

        created_cards = []
        for card_data in legacy_cards:
            card_data["description"] = "Migrée depuis l'ancien système"
            response = await client.post("/cards/", json=card_data, headers=user_headers)
            assert response.status_code == 200
            created_cards.append(response.json())

        # Vérifier que le système fonctionne avec les données migrées

        # 1. Lire toutes les listes
        lists_response = await client.get("/lists/", headers=admin_headers)
        assert lists_response.status_code == 200
        lists = lists_response.json()
        assert len(lists) == 3
        assert [lst["name"] for lst in lists] == ["A faire", "En cours", "Terminé"]

        # 2. Lire toutes les cartes
        cards_response = await client.get("/cards/", headers=user_headers)
        assert cards_response.status_code == 200
        cards = cards_response.json()
        assert len(cards) == 3

        # 3. Vérifier que les cartes sont correctement assignées
        cards_by_list = {}
        for card in cards:
            list_id = card["list_id"]
            if list_id not in cards_by_list:
                cards_by_list[list_id] = []
            cards_by_list[list_id].append(card)

        # Chaque liste par défaut doit avoir exactement 1 carte
        for lst in default_lists:
            assert lst["id"] in cards_by_list
            assert len(cards_by_list[lst["id"]]) == 1

        # 4. Tester l'évolution post-migration: ajouter de nouvelles listes
        new_list_response = await client.post(
            "/lists/", json={"name": "Nouvelle Liste Post-Migration", "order": 4}, headers=admin_headers
        )
        assert new_list_response.status_code == 200
        new_list = new_list_response.json()

        # 5. Déplacer une carte vers la nouvelle liste
        move_response = await client.put(
            f"/cards/{created_cards[0]['id']}/move",
            json={"list_id": new_list["id"], "position": 0},
            headers=user_headers,
        )
        assert move_response.status_code == 200

        # 6. Vérifier l'état final
        final_lists_response = await client.get("/lists/", headers=admin_headers)
        assert final_lists_response.status_code == 200
        final_lists = final_lists_response.json()
        assert len(final_lists) == 4

        final_cards_response = await client.get("/cards/", headers=user_headers)
        assert final_cards_response.status_code == 200
        final_cards = final_cards_response.json()
        assert len(final_cards) == 3

        # Vérifier que la carte a bien été déplacée
        moved_card = next(card for card in final_cards if card["id"] == created_cards[0]["id"])
        assert moved_card["list_id"] == new_list["id"]
