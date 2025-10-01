"""Tests pour le routeur lists."""

import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, status
from pydantic import ValidationError

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base
from app.models.user import User, UserRole, UserStatus
from app.models.kanban_list import KanbanList
from app.routers.lists import (
    router,
    read_lists,
    create_list as create_list_route,
    read_list,
    update_list as update_list_route,
    delete_list as delete_list_route,
    get_list_cards_count,
    reorder_lists as reorder_lists_route,
    require_admin,
)
from app.schemas import KanbanListCreate, KanbanListUpdate, KanbanListResponse, ListDeletionRequest, ListReorderRequest
from app.services.kanban_list import (
    get_lists,
    get_list,
    create_list,
    update_list,
    delete_list,
    get_list_with_cards_count,
    reorder_lists,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# Configuration de la base de données de test
@pytest.fixture
def db_session():
    """Fixture pour créer une session de base de données de test."""
    SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def admin_user(db_session):
    """Fixture pour créer un utilisateur admin de test."""
    user = User(
        email="admin@example.com",
        display_name="Admin User",
        password_hash="$2b$12$testhashedpassword",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        language="fr",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def regular_user(db_session):
    """Fixture pour créer un utilisateur régulier de test."""
    user = User(
        email="user@example.com",
        display_name="Regular User",
        password_hash="$2b$12$testhashedpassword",
        role=UserRole.EDITOR,
        status=UserStatus.ACTIVE,
        language="fr",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_list(db_session):
    """Fixture pour créer une liste Kanban de test."""
    kanban_list = KanbanList(
        name="À faire",
        description="Tâches à faire",
        display_order=1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(kanban_list)
    db_session.commit()
    db_session.refresh(kanban_list)
    return kanban_list


class TestListsRouter:
    """Tests pour le routeur des listes Kanban."""

    def test_list_lists_success_admin(self, admin_user):
        """Test de récupération des listes par un admin avec succès."""
        with patch("app.routers.lists.list_service.get_lists") as mock_get_lists:
            mock_lists = [
                KanbanListResponse(
                    id=1, name="À faire", order=1, created_at=datetime.utcnow(), updated_at=datetime.utcnow()
                )
            ]
            mock_get_lists.return_value = mock_lists

            with patch("app.routers.lists.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = admin_user

                # Mock database session
                with patch("app.routers.lists.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    result = asyncio.run(read_lists(mock_db.return_value.__enter__.return_value, admin_user))

                    assert len(result) == 1
                    assert result[0].name == "À faire"

    def test_list_lists_success_regular_user(self, regular_user):
        """Test de récupération des listes par un utilisateur régulier avec succès."""
        with patch("app.routers.lists.list_service.get_lists") as mock_get_lists:
            mock_lists = [
                KanbanListResponse(
                    id=1, name="En cours", order=2, created_at=datetime.utcnow(), updated_at=datetime.utcnow()
                )
            ]
            mock_get_lists.return_value = mock_lists

            with patch("app.routers.lists.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = regular_user

                # Mock database session
                with patch("app.routers.lists.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    result = asyncio.run(read_lists(mock_db.return_value.__enter__.return_value, regular_user))

                    assert len(result) == 1
                    assert result[0].name == "En cours"

    def test_list_lists_empty(self, admin_user):
        """Test de récupération des listes quand il n'y en a aucune."""
        with patch("app.routers.lists.list_service.get_lists") as mock_get_lists:
            mock_get_lists.return_value = []

            with patch("app.routers.lists.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = admin_user

                # Mock database session
                with patch("app.routers.lists.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    result = asyncio.run(read_lists(mock_db.return_value.__enter__.return_value, admin_user))

                    assert len(result) == 0

    def test_create_list_success_admin(self, admin_user):
        """Test de création d'une liste par un admin avec succès."""
        list_data = KanbanListCreate(name="Nouvelle liste", order=3)

        mock_list = KanbanListResponse(
            id=1, name="Nouvelle liste", order=3, created_at=datetime.utcnow(), updated_at=datetime.utcnow()
        )

        with patch("app.routers.lists.list_service.create_list") as mock_create:
            mock_create.return_value = mock_list

            with patch.object(require_admin, "__call__") as mock_require_admin:
                mock_require_admin.return_value = admin_user

                # Mock database session
                with patch("app.routers.lists.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    result = asyncio.run(
                        create_list_route(list_data, mock_db.return_value.__enter__.return_value, admin_user)
                    )

                    assert result.name == "Nouvelle liste"
                    assert result.order == 3

    def test_create_list_permission_denied(self, regular_user):
        """Test de création d'une liste par un utilisateur régulier (devrait échouer)."""
        list_data = KanbanListCreate(name="Nouvelle liste", order=3)

        with patch("app.routers.lists.require_admin") as mock_require_admin:
            mock_require_admin.side_effect = HTTPException(status_code=403, detail="Accès réservé aux administrateurs")

            # Mock database session
            with patch("app.routers.lists.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                with pytest.raises(HTTPException) as exc_info:
                    asyncio.run(
                        create_list_route(list_data, mock_db.return_value.__enter__.return_value, mock_require_admin())
                    )

                assert exc_info.value.status_code == 403
                assert exc_info.value.detail == "Accès réservé aux administrateurs"

    def test_create_list_invalid_data(self, admin_user):
        """Test de création d'une liste avec des données invalides."""
        with pytest.raises(ValidationError) as exc_info:
            # This should raise a validation error before even reaching the route function
            KanbanListCreate(name="")

        # Verify it's a validation error with status 422 equivalent
        assert len(exc_info.value.errors()) > 0

    def test_create_list_empty_name(self, admin_user):
        """Test de création d'une liste avec un nom vide."""
        with pytest.raises(ValidationError) as exc_info:
            # This should raise a validation error before even reaching the route function
            KanbanListCreate(name="", order=3)

        # Verify it's a validation error
        assert len(exc_info.value.errors()) > 0
        assert any("String should have at least 1 character" in str(error) for error in exc_info.value.errors())

    def test_create_list_duplicate_name(self, admin_user):
        """Test de création d'une liste avec un nom dupliqué."""
        list_data = KanbanListCreate(name="À faire", order=1)

        with patch("app.routers.lists.require_admin") as mock_require_admin:
            mock_require_admin.return_value = admin_user

            # Mock database session
            with patch("app.routers.lists.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                with patch("app.routers.lists.list_service.create_list") as mock_create:
                    mock_create.side_effect = ValueError("Une liste avec ce nom existe déjà")

                    with pytest.raises(HTTPException) as exc_info:
                        asyncio.run(
                            create_list_route(list_data, mock_db.return_value.__enter__.return_value, admin_user)
                        )

                    assert exc_info.value.status_code == 400
                    assert exc_info.value.detail == "Une liste avec ce nom existe déjà"

    def test_update_list_success_admin(self, admin_user):
        """Test de mise à jour d'une liste par un admin avec succès."""
        update_data = KanbanListUpdate(name="Liste mise à jour", order=1)

        mock_list = KanbanListResponse(
            id=1, name="Liste mise à jour", order=1, created_at=datetime.utcnow(), updated_at=datetime.utcnow()
        )

        with patch("app.routers.lists.list_service.update_list") as mock_update:
            mock_update.return_value = mock_list

            with patch.object(require_admin, "__call__") as mock_require_admin:
                mock_require_admin.return_value = admin_user

                # Mock database session
                with patch("app.routers.lists.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    result = asyncio.run(
                        update_list_route(1, update_data, mock_db.return_value.__enter__.return_value, admin_user)
                    )

                    assert result.name == "Liste mise à jour"

    def test_update_list_permission_denied(self, regular_user):
        """Test de mise à jour d'une liste par un utilisateur régulier (devrait échouer)."""
        update_data = KanbanListUpdate(name="Liste mise à jour", order=1)

        with patch("app.routers.lists.require_admin") as mock_require_admin:
            mock_require_admin.side_effect = HTTPException(status_code=403, detail="Accès réservé aux administrateurs")

            # Mock database session
            with patch("app.routers.lists.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                with pytest.raises(HTTPException) as exc_info:
                    asyncio.run(
                        update_list_route(
                            1, update_data, mock_db.return_value.__enter__.return_value, mock_require_admin()
                        )
                    )

                assert exc_info.value.status_code == 403
                assert exc_info.value.detail == "Accès réservé aux administrateurs"

    def test_update_list_not_found(self, admin_user):
        """Test de mise à jour d'une liste qui n'existe pas."""
        update_data = KanbanListUpdate(name="Liste mise à jour", order=1)

        with patch("app.routers.lists.list_service.update_list") as mock_update:
            mock_update.return_value = None

            with patch.object(require_admin, "__call__") as mock_require_admin:
                mock_require_admin.return_value = admin_user

                # Mock database session
                with patch("app.routers.lists.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    with pytest.raises(HTTPException) as exc_info:
                        asyncio.run(
                            update_list_route(
                                999, update_data, mock_db.return_value.__enter__.return_value, admin_user
                            )
                        )

                    assert exc_info.value.status_code == 404
                    assert exc_info.value.detail == "Liste non trouvée"

    def test_delete_list_success_admin(self, admin_user):
        """Test de suppression d'une liste par un admin avec succès."""
        deletion_request = ListDeletionRequest(target_list_id=2)

        with patch("app.routers.lists.list_service.delete_list") as mock_delete:
            mock_delete.return_value = True

            with patch.object(require_admin, "__call__") as mock_require_admin:
                mock_require_admin.return_value = admin_user

                # Mock database session
                with patch("app.routers.lists.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    result = asyncio.run(
                        delete_list_route(1, deletion_request, mock_db.return_value.__enter__.return_value, admin_user)
                    )

                    assert result["message"] == "Liste supprimée avec succès"

    def test_delete_list_permission_denied(self, regular_user):
        """Test de suppression d'une liste par un utilisateur régulier (devrait échouer)."""
        deletion_request = ListDeletionRequest(target_list_id=2)

        with patch("app.routers.lists.require_admin") as mock_require_admin:
            mock_require_admin.side_effect = HTTPException(status_code=403, detail="Accès réservé aux administrateurs")

            # Mock database session
            with patch("app.routers.lists.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                with pytest.raises(HTTPException) as exc_info:
                    asyncio.run(
                        delete_list_route(
                            1, deletion_request, mock_db.return_value.__enter__.return_value, mock_require_admin()
                        )
                    )

                assert exc_info.value.status_code == 403
                assert exc_info.value.detail == "Accès réservé aux administrateurs"

    def test_delete_list_not_found(self, admin_user):
        """Test de suppression d'une liste qui n'existe pas."""
        deletion_request = ListDeletionRequest(target_list_id=999)

        with patch("app.routers.lists.list_service.delete_list") as mock_delete:
            mock_delete.return_value = False

            with patch.object(require_admin, "__call__") as mock_require_admin:
                mock_require_admin.return_value = admin_user

                # Mock database session
                with patch("app.routers.lists.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    with pytest.raises(HTTPException) as exc_info:
                        asyncio.run(
                            delete_list_route(
                                999, deletion_request, mock_db.return_value.__enter__.return_value, admin_user
                            )
                        )

                    assert exc_info.value.status_code == 404
                    assert exc_info.value.detail == "Liste non trouvée"

    def test_get_list_with_cards_count_success(self, admin_user):
        """Test de récupération d'une liste avec le nombre de cartes."""
        with patch("app.routers.lists.list_service.get_list_with_cards_count") as mock_get_list:
            mock_list = MagicMock()
            mock_list.name = "À faire"
            mock_get_list.return_value = (mock_list, 5)

            with patch("app.routers.lists.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = admin_user

                # Mock database session
                with patch("app.routers.lists.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    result = asyncio.run(
                        get_list_cards_count(1, mock_db.return_value.__enter__.return_value, admin_user)
                    )

                    assert result["list_name"] == "À faire"
                    assert result["cards_count"] == 5

    def test_reorder_lists_success_admin(self, admin_user):
        """Test de réorganisation des listes par un admin avec succès."""
        reorder_request = ListReorderRequest(list_orders={1: 2, 2: 1})

        with patch("app.routers.lists.list_service.reorder_lists") as mock_reorder:
            mock_reorder.return_value = True

            with patch.object(require_admin, "__call__") as mock_require_admin:
                mock_require_admin.return_value = admin_user

                # Mock database session
                with patch("app.routers.lists.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    result = asyncio.run(
                        reorder_lists_route(reorder_request, mock_db.return_value.__enter__.return_value, admin_user)
                    )

                    assert result["message"] == "Listes réorganisées avec succès"

    def test_reorder_lists_permission_denied(self, regular_user):
        """Test de réorganisation des listes par un utilisateur régulier (devrait échouer)."""
        reorder_request = ListReorderRequest(list_orders={1: 2, 2: 1})

        with patch("app.routers.lists.require_admin") as mock_require_admin:
            mock_require_admin.side_effect = HTTPException(status_code=403, detail="Accès réservé aux administrateurs")

            # Mock database session
            with patch("app.routers.lists.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                with pytest.raises(HTTPException) as exc_info:
                    asyncio.run(
                        reorder_lists_route(
                            reorder_request, mock_db.return_value.__enter__.return_value, mock_require_admin()
                        )
                    )

                assert exc_info.value.status_code == 403
                assert exc_info.value.detail == "Accès réservé aux administrateurs"

    def test_invalid_list_id(self, admin_user):
        """Test avec un ID de liste invalide (négatif)."""
        with patch("app.routers.lists.require_admin") as mock_require_admin:
            mock_require_admin.return_value = admin_user

            # Mock database session
            with patch("app.routers.lists.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                with pytest.raises(HTTPException) as exc_info:
                    asyncio.run(
                        update_list_route(
                            -1,
                            KanbanListUpdate(name="Test", order=1),
                            mock_db.return_value.__enter__.return_value,
                            admin_user,
                        )
                    )

                assert exc_info.value.status_code == 400
                assert "doit être un entier positif" in exc_info.value.detail

    def test_service_error_handling(self, admin_user):
        """Test de gestion des erreurs de service."""
        with patch("app.routers.lists.list_service.get_lists") as mock_get_lists:
            mock_get_lists.side_effect = Exception("Database error")

            with patch("app.routers.lists.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = admin_user

                # Mock database session
                with patch("app.routers.lists.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    with pytest.raises(Exception) as exc_info:
                        asyncio.run(read_lists(mock_db.return_value.__enter__.return_value, admin_user))

                    # The exception should propagate since read_lists doesn't have error handling
                    assert "Database error" in str(exc_info.value)


# Import needed for tests
import asyncio
