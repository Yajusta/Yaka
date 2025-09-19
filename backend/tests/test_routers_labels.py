"""Tests pour le routeur labels."""

import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, status

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base
from app.models.label import Label
from app.models.user import User, UserRole, UserStatus
from app.routers.labels import create_label as create_label_route
from app.routers.labels import delete_label as delete_label_route
from app.routers.labels import read_label, read_labels, router
from app.routers.labels import update_label as update_label_route
from app.schemas import LabelCreate, LabelResponse, LabelUpdate
from app.services.label import create_label, delete_label, get_label, get_label_by_name, get_labels, update_label
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
        role=UserRole.USER,
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
def test_label(db_session):
    """Fixture pour créer un libellé de test."""
    label = Label(
        nom="Bug",
        couleur="#FF0000",
        description="Problème à corriger",
        created_by=1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(label)
    db_session.commit()
    db_session.refresh(label)
    return label


class TestLabelsRouter:
    """Tests pour le routeur des libellés."""

    def test_list_labels_success_admin(self, admin_user):
        """Test de récupération des libellés par un admin avec succès."""
        with patch("app.routers.labels.label_service.get_labels") as mock_get_labels:
            mock_labels = [
                LabelResponse(
                    id=1,
                    nom="Bug",
                    couleur="#FF0000",
                    description="Problème à corriger",
                    created_by=1,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
            ]
            mock_get_labels.return_value = mock_labels

            with patch("app.routers.labels.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = admin_user

                # Mock database session
                with patch("app.routers.labels.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    result = asyncio.run(read_labels(0, 100, mock_db.return_value.__enter__.return_value, admin_user))

                    assert len(result) == 1
                    assert result[0].nom == "Bug"

    def test_list_labels_success_regular_user(self, regular_user):
        """Test de récupération des libellés par un utilisateur régulier avec succès."""
        with patch("app.routers.labels.label_service.get_labels") as mock_get_labels:
            mock_labels = [
                LabelResponse(
                    id=1,
                    nom="Feature",
                    couleur="#00FF00",
                    description="Nouvelle fonctionnalité",
                    created_by=1,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
            ]
            mock_get_labels.return_value = mock_labels

            with patch("app.routers.labels.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = regular_user

                # Mock database session
                with patch("app.routers.labels.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    result = asyncio.run(
                        read_labels(0, 100, mock_db.return_value.__enter__.return_value, regular_user)
                    )

                    assert len(result) == 1
                    assert result[0].nom == "Feature"

    def test_list_labels_empty(self, admin_user):
        """Test de récupération des libellés quand il n'y en a aucun."""
        with patch("app.routers.labels.label_service.get_labels") as mock_get_labels:
            mock_get_labels.return_value = []

            with patch("app.routers.labels.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = admin_user

                # Mock database session
                with patch("app.routers.labels.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    result = asyncio.run(read_labels(0, 100, mock_db.return_value.__enter__.return_value, admin_user))

                    assert len(result) == 0

    def test_create_label_success_admin(self, admin_user):
        """Test de création d'un libellé par un admin avec succès."""
        label_data = LabelCreate(nom="Urgent", couleur="#FF0000", description="Priorité haute")

        mock_label = LabelResponse(
            id=1,
            nom="Urgent",
            couleur="#FF0000",
            description="Priorité haute",
            created_by=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        with patch("app.routers.labels.label_service.get_label_by_name") as mock_get_by_name:
            mock_get_by_name.return_value = None

            with patch("app.routers.labels.label_service.create_label") as mock_create:
                mock_create.return_value = mock_label

                with patch("app.routers.labels.get_current_active_user") as mock_current_user:
                    mock_current_user.return_value = admin_user

                    # Mock database session
                    with patch("app.routers.labels.get_db") as mock_db:
                        mock_db.return_value.__enter__.return_value = MagicMock()

                        result = asyncio.run(
                            create_label_route(label_data, mock_db.return_value.__enter__.return_value, admin_user)
                        )

                    assert result.nom == "Urgent"
                    assert result.couleur == "#FF0000"

    def test_create_label_permission_denied(self, regular_user):
        """Test de création d'un libellé par un utilisateur régulier (devrait échouer)."""
        label_data = LabelCreate(nom="Urgent", couleur="#FF0000", description="Priorité haute")

        with patch("app.routers.labels.require_admin") as mock_require_admin:
            mock_require_admin.side_effect = HTTPException(status_code=403, detail="Accès réservé aux administrateurs")

            with patch("app.routers.labels.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                with pytest.raises(HTTPException) as exc_info:
                    asyncio.run(
                        create_label_route(
                            label_data, mock_db.return_value.__enter__.return_value, mock_require_admin()
                        )
                    )

                assert exc_info.value.status_code == 403
                assert exc_info.value.detail == "Accès réservé aux administrateurs"

    def test_create_label_invalid_data(self, admin_user):
        """Test de création d'un libellé avec des données invalides."""
        with patch("app.routers.labels.require_admin") as mock_require_admin:
            mock_require_admin.return_value = admin_user

            with patch("app.routers.labels.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                with pytest.raises(HTTPException) as exc_info:
                    asyncio.run(
                        create_label_route(
                            None, mock_db.return_value.__enter__.return_value, mock_require_admin.return_value
                        )
                    )

                assert exc_info.value.status_code == 422

    def test_create_label_empty_name(self, admin_user):
        """Test de création d'un libellé avec un nom vide."""
        label_data = LabelCreate(nom="", couleur="#FF0000", description="Priorité haute")

        with patch("app.routers.labels.require_admin") as mock_require_admin:
            mock_require_admin.return_value = admin_user

            with patch("app.routers.labels.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                with patch("app.routers.labels.label_service.get_label_by_name") as mock_get_by_name:
                    mock_get_by_name.return_value = None

                    with patch("app.routers.labels.label_service.create_label") as mock_create:
                        mock_create.side_effect = ValueError("Le nom ne peut pas être vide")

                        with pytest.raises(HTTPException) as exc_info:
                            asyncio.run(
                                create_label_route(
                                    label_data,
                                    mock_db.return_value.__enter__.return_value,
                                    mock_require_admin.return_value,
                                )
                            )

                        assert exc_info.value.status_code == 400
                        assert exc_info.value.detail == "Le nom ne peut pas être vide"

    def test_create_label_duplicate_name(self, admin_user):
        """Test de création d'un libellé avec un nom dupliqué."""
        label_data = LabelCreate(nom="Bug", couleur="#FF0000", description="Problème à corriger")

        with patch("app.routers.labels.get_current_active_user") as mock_current_user:
            mock_current_user.return_value = admin_user

            # Mock database session
            with patch("app.routers.labels.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                with patch("app.routers.labels.label_service.create_label") as mock_create:
                    mock_create.side_effect = ValueError("Un libellé avec ce nom existe déjà")

                    with pytest.raises(HTTPException) as exc_info:
                        asyncio.run(
                            create_label_route(label_data, mock_db.return_value.__enter__.return_value, admin_user)
                        )

                    assert exc_info.value.status_code == 400
                    assert exc_info.value.detail == "Un libellé avec ce nom existe déjà"

    def test_update_label_success_admin(self, admin_user):
        """Test de mise à jour d'un libellé par un admin avec succès."""
        update_data = LabelUpdate(nom="Updated Bug", couleur="#FFFF00", description="Problème critique")

        mock_label = LabelResponse(
            id=1,
            nom="Updated Bug",
            couleur="#FFFF00",
            description="Problème critique",
            created_by=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        with patch("app.routers.labels.label_service.update_label") as mock_update:
            mock_update.return_value = mock_label

            with patch("app.routers.labels.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = admin_user

                # Mock database session
                with patch("app.routers.labels.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    result = asyncio.run(
                        update_label_route(1, update_data, mock_db.return_value.__enter__.return_value, admin_user)
                    )

                    assert result.nom == "Updated Bug"
                    assert result.couleur == "#FFFF00"

    def test_update_label_permission_denied(self, regular_user):
        """Test de mise à jour d'un libellé par un utilisateur régulier (devrait échouer)."""
        update_data = LabelUpdate(nom="Updated Bug", couleur="#FFFF00", description="Problème critique")

        with patch("app.routers.labels.require_admin") as mock_require_admin:
            mock_require_admin.side_effect = HTTPException(status_code=403, detail="Accès réservé aux administrateurs")

            # Mock database session
            with patch("app.routers.labels.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                with pytest.raises(HTTPException) as exc_info:
                    asyncio.run(
                        update_label_route(
                            1, update_data, mock_db.return_value.__enter__.return_value, mock_require_admin()
                        )
                    )

                assert exc_info.value.status_code == 403
                assert exc_info.value.detail == "Accès réservé aux administrateurs"

    def test_update_label_not_found(self, admin_user):
        """Test de mise à jour d'un libellé qui n'existe pas."""
        update_data = LabelUpdate(nom="Updated Bug")

        with patch("app.routers.labels.label_service.update_label") as mock_update:
            mock_update.return_value = None

            with patch("app.routers.labels.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = admin_user

                # Mock database session
                with patch("app.routers.labels.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    with pytest.raises(HTTPException) as exc_info:
                        asyncio.run(
                            update_label_route(
                                999, update_data, mock_db.return_value.__enter__.return_value, admin_user
                            )
                        )

                    assert exc_info.value.status_code == 404
                    assert exc_info.value.detail == "Libellé non trouvé"

    def test_delete_label_success_admin(self, admin_user):
        """Test de suppression d'un libellé par un admin avec succès."""
        with patch("app.routers.labels.label_service.delete_label") as mock_delete:
            mock_delete.return_value = True

            with patch("app.routers.labels.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = admin_user

                # Mock database session
                with patch("app.routers.labels.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    result = asyncio.run(
                        delete_label_route(1, mock_db.return_value.__enter__.return_value, admin_user)
                    )

                    assert result["message"] == "Libellé supprimé avec succès"

    def test_delete_label_permission_denied(self, regular_user):
        """Test de suppression d'un libellé par un utilisateur régulier (devrait échouer)."""
        with patch("app.routers.labels.require_admin") as mock_require_admin:
            mock_require_admin.side_effect = HTTPException(status_code=403, detail="Accès réservé aux administrateurs")

            # Mock database session
            with patch("app.routers.labels.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                with pytest.raises(HTTPException) as exc_info:
                    asyncio.run(
                        delete_label_route(1, mock_db.return_value.__enter__.return_value, mock_require_admin())
                    )

                assert exc_info.value.status_code == 403
                assert exc_info.value.detail == "Accès réservé aux administrateurs"

    def test_delete_label_not_found(self, admin_user):
        """Test de suppression d'un libellé qui n'existe pas."""
        with patch("app.routers.labels.label_service.delete_label") as mock_delete:
            mock_delete.return_value = False

            with patch("app.routers.labels.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = admin_user

                # Mock database session
                with patch("app.routers.labels.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    with pytest.raises(HTTPException) as exc_info:
                        asyncio.run(delete_label_route(999, mock_db.return_value.__enter__.return_value, admin_user))

                    assert exc_info.value.status_code == 404
                    assert exc_info.value.detail == "Libellé non trouvé"

    def test_invalid_label_id(self, admin_user):
        """Test avec un ID de libellé invalide."""
        with patch("app.routers.labels.require_admin") as mock_require_admin:
            mock_require_admin.return_value = admin_user

            # Mock database session
            with patch("app.routers.labels.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                with pytest.raises(HTTPException) as exc_info:
                    asyncio.run(
                        update_label_route("invalid", None, mock_db.return_value.__enter__.return_value, admin_user)
                    )

                assert exc_info.value.status_code == 422

    def test_invalid_color_format(self, admin_user):
        """Test avec un format de couleur invalide."""
        label_data = LabelCreate(nom="Test Label", couleur="invalid_color", description="Test description")

        with patch("app.routers.labels.require_admin") as mock_require_admin:
            mock_require_admin.return_value = admin_user

            # Mock database session
            with patch("app.routers.labels.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                with patch("app.routers.labels.label_service.get_label_by_name") as mock_get_by_name:
                    mock_get_by_name.side_effect = ValueError("Format de couleur invalide")

                    with pytest.raises(HTTPException) as exc_info:
                        asyncio.run(
                            create_label_route(label_data, mock_db.return_value.__enter__.return_value, admin_user)
                        )

                    assert exc_info.value.status_code == 400
                    assert exc_info.value.detail == "Format de couleur invalide"

    def test_service_error_handling(self, admin_user):
        """Test de gestion des erreurs de service."""
        with patch("app.routers.labels.label_service.get_labels") as mock_get_labels:
            mock_get_labels.side_effect = Exception("Database error")

            with patch("app.routers.labels.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = admin_user

                # Mock database session
                with patch("app.routers.labels.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    with pytest.raises(Exception) as exc_info:
                        asyncio.run(read_labels(0, 100, mock_db.return_value.__enter__.return_value, admin_user))

                    assert str(exc_info.value) == "Database error"


# Import needed for tests
import asyncio
