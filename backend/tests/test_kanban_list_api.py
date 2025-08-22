"""Tests pour l'API des listes Kanban."""

import pytest
import sys
import os
from unittest.mock import Mock, patch

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
    # Authentification avec l'admin par défaut
    resp_login = await client.post("/auth/login", data={"username": "admin@yaka.local", "password": "admin123"})
    assert resp_login.status_code == 200
    token = resp_login.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def user_headers(client, db_session):
    """Fixture pour obtenir les headers d'authentification utilisateur normal."""
    # Créer un utilisateur normal pour les tests
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


@pytest.fixture
def sample_lists(db_session):
    """Fixture pour créer des listes d'exemple."""
    # Nettoyer les listes existantes
    db_session.query(KanbanList).delete()
    db_session.commit()

    lists = [
        KanbanList(name="A faire", order=1),
        KanbanList(name="En cours", order=2),
        KanbanList(name="Terminé", order=3),
    ]

    for lst in lists:
        db_session.add(lst)
    db_session.commit()

    for lst in lists:
        db_session.refresh(lst)

    yield lists

    # Nettoyer après le test
    db_session.query(KanbanList).delete()
    db_session.commit()


class TestKanbanListAPI:
    """Tests pour l'API des listes Kanban."""

    @pytest.mark.asyncio
    async def test_get_lists_empty(self, client, admin_headers, db_session):
        """Test de récupération des listes quand aucune n'existe."""
        # Arrange - Nettoyer toutes les listes
        db_session.query(KanbanList).delete()
        db_session.commit()

        # Act
        response = await client.get("/lists/", headers=admin_headers)

        # Assert
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_get_lists_success(self, client, admin_headers, sample_lists):
        """Test de récupération des listes avec succès."""
        # Act
        response = await client.get("/lists/", headers=admin_headers)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0]["name"] == "A faire"
        assert data[0]["order"] == 1
        assert data[1]["name"] == "En cours"
        assert data[1]["order"] == 2
        assert data[2]["name"] == "Terminé"
        assert data[2]["order"] == 3

    @pytest.mark.asyncio
    async def test_get_lists_user_access(self, client, user_headers, sample_lists):
        """Test que les utilisateurs normaux peuvent récupérer les listes."""
        # Act
        response = await client.get("/lists/", headers=user_headers)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    @pytest.mark.asyncio
    async def test_get_lists_unauthorized(self, client, sample_lists):
        """Test de récupération des listes sans authentification."""
        # Act
        response = await client.get("/lists/")

        # Assert
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_list_success(self, client, admin_headers):
        """Test de création d'une liste avec succès."""
        # Arrange
        list_data = {"name": "Nouvelle Liste", "order": 1}

        # Act
        response = await client.post("/lists/", json=list_data, headers=admin_headers)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Nouvelle Liste"
        assert data["order"] == 1
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_list_user_forbidden(self, client, user_headers):
        """Test que les utilisateurs normaux ne peuvent pas créer de listes."""
        # Arrange
        list_data = {"name": "Nouvelle Liste", "order": 1}

        # Act
        response = await client.post("/lists/", json=list_data, headers=user_headers)

        # Assert
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_list_unauthorized(self, client):
        """Test de création d'une liste sans authentification."""
        # Arrange
        list_data = {"name": "Nouvelle Liste", "order": 1}

        # Act
        response = await client.post("/lists/", json=list_data)

        # Assert
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_list_invalid_data(self, client, admin_headers):
        """Test de création d'une liste avec des données invalides."""
        # Test nom vide
        response = await client.post("/lists/", json={"name": "", "order": 1}, headers=admin_headers)
        assert response.status_code == 422

        # Test ordre négatif
        response = await client.post("/lists/", json={"name": "Test List", "order": 0}, headers=admin_headers)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_list_duplicate_name(self, client, admin_headers, sample_lists):
        """Test de création d'une liste avec un nom déjà existant."""
        # Arrange
        list_data = {"name": "A faire", "order": 4}  # Nom déjà existant

        # Act
        response = await client.post("/lists/", json=list_data, headers=admin_headers)

        # Assert
        assert response.status_code == 400
        assert "existe déjà" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_list_success(self, client, admin_headers, sample_lists):
        """Test de récupération d'une liste par ID avec succès."""
        # Arrange
        list_id = sample_lists[0].id

        # Act
        response = await client.get(f"/lists/{list_id}", headers=admin_headers)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == list_id
        assert data["name"] == "A faire"

    @pytest.mark.asyncio
    async def test_get_list_not_found(self, client, admin_headers):
        """Test de récupération d'une liste inexistante."""
        # Act
        response = await client.get("/lists/999", headers=admin_headers)

        # Assert
        assert response.status_code == 404
        assert "non trouvée" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_list_success(self, client, admin_headers, sample_lists):
        """Test de mise à jour d'une liste avec succès."""
        # Arrange
        list_id = sample_lists[0].id
        update_data = {"name": "Nouveau Nom"}

        # Act
        response = await client.put(f"/lists/{list_id}", json=update_data, headers=admin_headers)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Nouveau Nom"
        assert data["order"] == 1  # Ordre inchangé

    @pytest.mark.asyncio
    async def test_update_list_user_forbidden(self, client, user_headers, sample_lists):
        """Test que les utilisateurs normaux ne peuvent pas modifier les listes."""
        # Arrange
        list_id = sample_lists[0].id
        update_data = {"name": "Nouveau Nom"}

        # Act
        response = await client.put(f"/lists/{list_id}", json=update_data, headers=user_headers)

        # Assert
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_list_not_found(self, client, admin_headers):
        """Test de mise à jour d'une liste inexistante."""
        # Act
        response = await client.put("/lists/999", json={"name": "Nouveau Nom"}, headers=admin_headers)

        # Assert
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_list_invalid_id(self, client, admin_headers):
        """Test de mise à jour avec un ID invalide."""
        # Act
        response = await client.put("/lists/0", json={"name": "Nouveau Nom"}, headers=admin_headers)

        # Assert
        assert response.status_code == 400
        assert "entier positif" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_list_success(self, client, admin_headers, sample_lists):
        """Test de suppression d'une liste avec succès."""
        # Arrange
        list_to_delete_id = sample_lists[1].id  # "En cours"
        target_list_id = sample_lists[0].id  # "A faire"

        deletion_data = {"target_list_id": target_list_id}

        # Act
        response = await client.delete(f"/lists/{list_to_delete_id}", json=deletion_data, headers=admin_headers)

        # Assert
        assert response.status_code == 200
        assert "supprimée avec succès" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_delete_list_user_forbidden(self, client, user_headers, sample_lists):
        """Test que les utilisateurs normaux ne peuvent pas supprimer les listes."""
        # Arrange
        list_id = sample_lists[0].id
        deletion_data = {"target_list_id": sample_lists[1].id}

        # Act
        response = await client.delete(f"/lists/{list_id}", json=deletion_data, headers=user_headers)

        # Assert
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_list_last_list(self, client, admin_headers, db_session):
        """Test de suppression de la dernière liste (doit échouer)."""
        # Arrange - Créer une seule liste
        db_session.query(KanbanList).delete()
        db_session.commit()

        single_list = KanbanList(name="Seule Liste", order=1)
        db_session.add(single_list)
        db_session.commit()
        db_session.refresh(single_list)

        deletion_data = {"target_list_id": single_list.id}

        # Act
        response = await client.delete(f"/lists/{single_list.id}", json=deletion_data, headers=admin_headers)

        # Assert
        assert response.status_code == 400
        assert "dernière liste" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_list_cards_count_success(self, client, admin_headers, sample_lists, db_session):
        """Test de récupération du nombre de cartes dans une liste."""
        # Arrange
        list_id = sample_lists[0].id

        # Créer des cartes dans cette liste
        cards = [
            Card(titre="Card 1", description="Desc 1", list_id=list_id, created_by=1, assignee_id=1),
            Card(titre="Card 2", description="Desc 2", list_id=list_id, created_by=1, assignee_id=1),
        ]

        for card in cards:
            db_session.add(card)
        db_session.commit()

        # Act
        response = await client.get(f"/lists/{list_id}/cards-count", headers=admin_headers)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["list_id"] == list_id
        assert data["cards_count"] == 2
        assert data["list_name"] == "A faire"

    @pytest.mark.asyncio
    async def test_get_list_cards_count_not_found(self, client, admin_headers):
        """Test de récupération du nombre de cartes pour une liste inexistante."""
        # Act
        response = await client.get("/lists/999/cards-count", headers=admin_headers)

        # Assert
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_list_cards_count_invalid_id(self, client, admin_headers):
        """Test de récupération du nombre de cartes avec un ID invalide."""
        # Act
        response = await client.get("/lists/0/cards-count", headers=admin_headers)

        # Assert
        assert response.status_code == 400
        assert "entier positif" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_reorder_lists_success(self, client, admin_headers, sample_lists):
        """Test de réorganisation des listes avec succès."""
        # Arrange
        reorder_data = {
            "list_orders": {
                str(sample_lists[0].id): 3,  # "A faire" -> ordre 3
                str(sample_lists[1].id): 1,  # "En cours" -> ordre 1
                str(sample_lists[2].id): 2,  # "Terminé" -> ordre 2
            }
        }

        # Act
        response = await client.post("/lists/reorder", json=reorder_data, headers=admin_headers)

        # Assert
        assert response.status_code == 200
        assert "réorganisées avec succès" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_reorder_lists_user_forbidden(self, client, user_headers, sample_lists):
        """Test que les utilisateurs normaux ne peuvent pas réorganiser les listes."""
        # Arrange
        reorder_data = {"list_orders": {str(sample_lists[0].id): 2, str(sample_lists[1].id): 1}}

        # Act
        response = await client.post("/lists/reorder", json=reorder_data, headers=user_headers)

        # Assert
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_reorder_lists_invalid_data(self, client, admin_headers, sample_lists):
        """Test de réorganisation avec des données invalides."""
        # Test ordres dupliqués
        reorder_data = {"list_orders": {str(sample_lists[0].id): 1, str(sample_lists[1].id): 1}}  # Ordre dupliqué

        response = await client.post("/lists/reorder", json=reorder_data, headers=admin_headers)
        assert response.status_code == 422
        assert "uniques" in response.json()["detail"][0]["msg"]

    @pytest.mark.asyncio
    async def test_reorder_lists_non_existing_list(self, client, admin_headers, sample_lists):
        """Test de réorganisation avec une liste inexistante."""
        # Arrange
        reorder_data = {"list_orders": {str(sample_lists[0].id): 1, "999": 2}}  # Liste inexistante

        # Act
        response = await client.post("/lists/reorder", json=reorder_data, headers=admin_headers)

        # Assert
        assert response.status_code == 400
        assert "n'existent pas" in response.json()["detail"]
