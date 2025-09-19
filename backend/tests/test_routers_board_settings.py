"""Tests pour le routeur board_settings."""

import asyncio
import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, status

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base
from app.models.user import User, UserRole, UserStatus
from app.routers.board_settings import (
    delete_board_setting,
    get_board_title,
    read_board_setting,
    read_board_settings,
    require_admin,
    router,
    update_board_setting,
    update_board_title,
)
from app.schemas.board_settings import BoardSettingsResponse, BoardTitleUpdate
from app.services.board_settings import (
    create_or_update_setting,
    delete_setting,
    get_all_settings,
    get_setting,
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
def test_app():
    """Fixture pour créer une application FastAPI de test."""
    from app.database import get_db
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)

    # Override the database dependency
    def override_get_db():
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return app


class TestBoardSettingsRouter:
    """Tests pour le routeur des paramètres du tableau."""

    def test_read_board_settings_as_admin(self, admin_user):
        """Test de récupération des paramètres du tableau en tant qu'admin."""
        with patch("app.routers.board_settings.board_settings_service.get_all_settings") as mock_get_all:
            mock_settings = [
                BoardSettingsResponse(
                    id=1,
                    setting_key="test_key",
                    setting_value="test_value",
                    description="Test setting",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
            ]
            mock_get_all.return_value = mock_settings

            with patch("app.routers.board_settings.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = admin_user

                # Mock the database session
                with patch("app.routers.board_settings.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    result = asyncio.run(
                        read_board_settings(
                            mock_db.return_value.__enter__.return_value,
                            mock_current_user.return_value,
                        )
                    )

                    assert len(result) == 1
                    assert result[0].setting_key == "test_key"

    def test_read_board_settings_as_user_forbidden(self, regular_user):
        """Test de tentative de récupération des paramètres en tant qu'utilisateur régulier."""
        with patch("app.routers.board_settings.get_current_active_user") as mock_current_user:
            mock_current_user.return_value = regular_user

            # Mock the database session
            with patch("app.routers.board_settings.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                with pytest.raises(HTTPException) as exc_info:
                    require_admin(mock_current_user.return_value)

                assert exc_info.value.status_code == 403
                assert exc_info.value.detail == "Accès réservé aux administrateurs"

    def test_get_board_title_public_access(self):
        """Test de récupération du titre du tableau (accès public)."""
        with patch("app.routers.board_settings.board_settings_service.get_board_title") as mock_get_title:
            mock_get_title.return_value = "Mon Tableau Kanban"

            # Mock the database session
            with patch("app.routers.board_settings.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                result = asyncio.run(get_board_title(mock_db.return_value.__enter__.return_value))

                assert result["title"] == "Mon Tableau Kanban"

    def test_update_board_title_as_admin(self, admin_user):
        """Test de mise à jour du titre du tableau en tant qu'admin."""
        with patch("app.routers.board_settings.board_settings_service.set_board_title") as mock_set_title:
            mock_setting = BoardSettingsResponse(
                id=2,
                setting_key="board_title",
                setting_value="Nouveau Titre",
                description="Titre du tableau",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            mock_set_title.return_value = mock_setting

            with patch("app.routers.board_settings.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = admin_user

                # Mock the database session
                with patch("app.routers.board_settings.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    result = asyncio.run(
                        update_board_title(
                            BoardTitleUpdate(title="Nouveau Titre"),
                            mock_db.return_value.__enter__.return_value,
                            mock_current_user.return_value,
                        )
                    )

                    assert result.setting_value == "Nouveau Titre"

    def test_update_board_title_as_user_forbidden(self, regular_user):
        """Test de tentative de mise à jour du titre en tant qu'utilisateur régulier."""
        with patch("app.routers.board_settings.get_current_active_user") as mock_current_user:
            mock_current_user.return_value = regular_user

            # Mock the database session
            with patch("app.routers.board_settings.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                with pytest.raises(HTTPException) as exc_info:
                    require_admin(mock_current_user.return_value)

                assert exc_info.value.status_code == 403
                assert exc_info.value.detail == "Accès réservé aux administrateurs"

    def test_read_board_setting_as_admin(self, admin_user):
        """Test de récupération d'un paramètre spécifique en tant qu'admin."""
        with patch("app.routers.board_settings.board_settings_service.get_setting") as mock_get_setting:
            mock_setting = BoardSettingsResponse(
                id=3,
                setting_key="test_key",
                setting_value="test_value",
                description="Test setting",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            mock_get_setting.return_value = mock_setting

            with patch("app.routers.board_settings.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = admin_user

                # Mock the database session
                with patch("app.routers.board_settings.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    result = asyncio.run(
                        read_board_setting(
                            "test_key",
                            mock_db.return_value.__enter__.return_value,
                            mock_current_user.return_value,
                        )
                    )

                    assert result.setting_key == "test_key"

    def test_read_board_setting_not_found(self, admin_user):
        """Test de récupération d'un paramètre qui n'existe pas."""
        with patch("app.routers.board_settings.board_settings_service.get_setting") as mock_get_setting:
            mock_get_setting.return_value = None

            with patch("app.routers.board_settings.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = admin_user

                # Mock the database session
                with patch("app.routers.board_settings.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    with pytest.raises(HTTPException) as exc_info:
                        asyncio.run(
                            read_board_setting(
                                "nonexistent_key",
                                mock_db.return_value.__enter__.return_value,
                                mock_current_user.return_value,
                            )
                        )

                    assert exc_info.value.status_code == 404
                    assert exc_info.value.detail == "Paramètre non trouvé"

    def test_update_board_setting_as_admin(self, admin_user):
        """Test de mise à jour d'un paramètre spécifique en tant qu'admin."""
        with patch("app.routers.board_settings.board_settings_service.create_or_update_setting") as mock_update:
            mock_setting = BoardSettingsResponse(
                id=4,
                setting_key="test_key",
                setting_value="new_value",
                description="Updated setting",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            mock_update.return_value = mock_setting

            with patch("app.routers.board_settings.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = admin_user

                # Mock the database session
                with patch("app.routers.board_settings.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    result = asyncio.run(
                        update_board_setting(
                            "test_key",
                            {"setting_value": "new_value", "description": "Updated setting"},
                            mock_db.return_value.__enter__.return_value,
                            mock_current_user.return_value,
                        )
                    )

                    assert result.setting_value == "new_value"

    def test_update_board_setting_missing_value(self, admin_user):
        """Test de mise à jour d'un paramètre sans setting_value."""
        with patch("app.routers.board_settings.get_current_active_user") as mock_current_user:
            mock_current_user.return_value = admin_user

            # Mock the database session
            with patch("app.routers.board_settings.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                with pytest.raises(HTTPException) as exc_info:
                    asyncio.run(
                        update_board_setting(
                            "test_key",
                            {"description": "Updated setting without value"},
                            mock_db.return_value.__enter__.return_value,
                            mock_current_user.return_value,
                        )
                    )

                assert exc_info.value.status_code == 400
                assert exc_info.value.detail == "setting_value est requis"

    def test_delete_board_setting_as_admin(self, admin_user):
        """Test de suppression d'un paramètre en tant qu'admin."""
        with patch("app.routers.board_settings.board_settings_service.delete_setting") as mock_delete:
            mock_delete.return_value = True

            with patch("app.routers.board_settings.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = admin_user

                # Mock the database session
                with patch("app.routers.board_settings.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    result = asyncio.run(
                        delete_board_setting(
                            "test_key",
                            mock_db.return_value.__enter__.return_value,
                            mock_current_user.return_value,
                        )
                    )

                    assert result["message"] == "Paramètre supprimé avec succès"

    def test_delete_board_setting_not_found(self, admin_user):
        """Test de suppression d'un paramètre qui n'existe pas."""
        with patch("app.routers.board_settings.board_settings_service.delete_setting") as mock_delete:
            mock_delete.return_value = False

            with patch("app.routers.board_settings.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = admin_user

                # Mock the database session
                with patch("app.routers.board_settings.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    with pytest.raises(HTTPException) as exc_info:
                        asyncio.run(
                            delete_board_setting(
                                "nonexistent_key",
                                mock_db.return_value.__enter__.return_value,
                                mock_current_user.return_value,
                            )
                        )

                    assert exc_info.value.status_code == 404
                    assert exc_info.value.detail == "Paramètre non trouvé"

    def test_require_admin_dependency_with_admin(self, admin_user):
        """Test du dependency require_admin avec un utilisateur admin."""
        result = require_admin(admin_user)
        assert result == admin_user

    def test_require_admin_dependency_with_user(self, regular_user):
        """Test du dependency require_admin avec un utilisateur régulier."""
        with pytest.raises(HTTPException) as exc_info:
            require_admin(regular_user)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Accès réservé aux administrateurs"

    def test_update_board_title_with_empty_title(self, admin_user):
        """Test de mise à jour du titre avec une chaîne vide."""
        with patch("app.routers.board_settings.get_current_active_user") as mock_current_user:
            mock_current_user.return_value = admin_user

            # Mock the database session
            with patch("app.routers.board_settings.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                with pytest.raises(HTTPException) as exc_info:
                    asyncio.run(
                        update_board_title(
                            BoardTitleUpdate(title=""),
                            mock_db.return_value.__enter__.return_value,
                            mock_current_user.return_value,
                        )
                    )

                assert exc_info.value.status_code == 422

    def test_update_board_setting_with_invalid_data(self, admin_user):
        """Test de mise à jour d'un paramètre avec des données invalides."""
        with patch("app.routers.board_settings.get_current_active_user") as mock_current_user:
            mock_current_user.return_value = admin_user

            # Mock the database session
            with patch("app.routers.board_settings.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                with pytest.raises(HTTPException) as exc_info:
                    asyncio.run(
                        update_board_setting(
                            "test_key",
                            {"invalid_field": "value"},
                            mock_db.return_value.__enter__.return_value,
                            mock_current_user.return_value,
                        )
                    )

                assert exc_info.value.status_code == 422

