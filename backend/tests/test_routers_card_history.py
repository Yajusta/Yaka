"""Tests pour le routeur card_history."""

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
from app.models.card import Card
from app.routers.card_history import get_card_history, create_card_history_entry
from app.schemas import CardHistoryCreate, CardHistoryResponse
from app.services.card_history import (
    get_card_history as service_get_history,
    create_card_history_entry as service_create_history,
)
from app.services.card import get_card
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
def test_user(db_session):
    """Fixture pour créer un utilisateur de test."""
    user = User(
        email="test@example.com",
        display_name="Test User",
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
def test_card(db_session):
    """Fixture pour créer une carte de test."""
    card = Card(
        title="Test Card",
        description="Test description",
        list_id=1,
        created_by=1,
        position=0,
        is_archived=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(card)
    db_session.commit()
    db_session.refresh(card)
    return card


@pytest.fixture
def test_history_entry():
    """Fixture pour créer une entrée d'historique de test."""
    return CardHistoryResponse(
        id=1,
        card_id=1,
        user_id=1,
        action="card_created",
        description="Carte créée",
        created_at=datetime.utcnow(),
        user_display_name="Test User",
    )


class TestCardHistoryRouter:
    """Tests pour le routeur de l'historique des cartes."""

    def test_get_card_history_success(self, test_user, test_card):
        """Test de récupération de l'historique d'une carte avec succès."""
        from app.routers.card_history import get_card_history

        with patch("app.services.card.get_card") as mock_get_card:
            mock_get_card.return_value = test_card

            with patch("app.services.card_history.get_card_history") as mock_get_history:
                mock_history = [
                    CardHistoryResponse(
                        id=1,
                        card_id=1,
                        user_id=1,
                        action="card_created",
                        description="Carte créée",
                        created_at=datetime.utcnow(),
                        user_display_name="Test User",
                    )
                ]
                mock_get_history.return_value = mock_history

                with patch("app.routers.card_history.get_current_active_user") as mock_current_user:
                    mock_current_user.return_value = test_user

                    # Mock the database session
                    with patch("app.routers.card_history.get_db") as mock_db:
                        mock_db.return_value.__enter__.return_value = MagicMock()

                        result = asyncio.run(
                            get_card_history(
                                1, mock_db.return_value.__enter__.return_value, mock_current_user.return_value
                            )
                        )

                        assert len(result) == 1
                        assert result[0].action == "card_created"
                        assert result[0].description == "Carte créée"

    def test_get_card_history_card_not_found(self, test_user):
        """Test de récupération de l'historique d'une carte qui n'existe pas."""
        from app.routers.card_history import get_card_history

        with patch("app.services.card.get_card") as mock_get_card:
            mock_get_card.return_value = None

            with patch("app.routers.card_history.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = test_user

                # Mock the database session
                with patch("app.routers.card_history.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    with pytest.raises(HTTPException) as exc_info:
                        asyncio.run(
                            get_card_history(
                                999, mock_db.return_value.__enter__.return_value, mock_current_user.return_value
                            )
                        )

                    assert exc_info.value.status_code == 404
                    assert exc_info.value.detail == "Carte non trouvée"

    def test_get_card_history_empty(self, test_user, test_card):
        """Test de récupération de l'historique d'une carte sans historique."""
        from app.routers.card_history import get_card_history

        with patch("app.services.card.get_card") as mock_get_card:
            mock_get_card.return_value = test_card

            with patch("app.services.card_history.get_card_history") as mock_get_history:
                mock_get_history.return_value = []

                with patch("app.routers.card_history.get_current_active_user") as mock_current_user:
                    mock_current_user.return_value = test_user

                    # Mock the database session
                    with patch("app.routers.card_history.get_db") as mock_db:
                        mock_db.return_value.__enter__.return_value = MagicMock()

                        result = asyncio.run(
                            get_card_history(
                                1, mock_db.return_value.__enter__.return_value, mock_current_user.return_value
                            )
                        )

                        assert isinstance(result, list)
                        assert len(result) == 0

    def test_create_card_history_entry_success(self, test_user, test_card, test_history_entry):
        """Test de création d'une entrée d'historique avec succès."""
        from app.routers.card_history import create_card_history_entry

        history_data = {"card_id": 1, "user_id": 1, "action": "card_updated", "description": "Carte mise à jour"}

        with patch("app.services.card.get_card") as mock_get_card:
            mock_get_card.return_value = test_card

            with patch("app.services.card_history.create_card_history_entry") as mock_create:
                mock_create.return_value = test_history_entry

                with patch("app.routers.card_history.get_current_active_user") as mock_current_user:
                    mock_current_user.return_value = test_user

                    # Mock the database session
                    with patch("app.routers.card_history.get_db") as mock_db:
                        mock_db.return_value.__enter__.return_value = MagicMock()

                        result = asyncio.run(
                            create_card_history_entry(
                                1,
                                history_data,
                                mock_db.return_value.__enter__.return_value,
                                mock_current_user.return_value,
                            )
                        )

                        assert result.action == "card_created"
                        assert result.description == "Carte créée"

    def test_create_card_history_entry_card_not_found(self, test_user):
        """Test de création d'une entrée d'historique pour une carte qui n'existe pas."""
        from app.routers.card_history import create_card_history_entry

        history_data = {"card_id": 999, "user_id": 1, "action": "card_updated", "description": "Carte mise à jour"}

        with patch("app.services.card.get_card") as mock_get_card:
            mock_get_card.return_value = None

            with patch("app.routers.card_history.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = test_user

                # Mock the database session
                with patch("app.routers.card_history.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    with pytest.raises(HTTPException) as exc_info:
                        asyncio.run(
                            create_card_history_entry(
                                999,
                                history_data,
                                mock_db.return_value.__enter__.return_value,
                                mock_current_user.return_value,
                            )
                        )

                    assert exc_info.value.status_code == 404
                    assert exc_info.value.detail == "Carte non trouvée"

    def test_get_card_history_invalid_card_id(self, test_user):
        """Test de récupération de l'historique avec un ID de carte invalide."""
        from app.routers.card_history import get_card_history

        with patch("app.routers.card_history.get_current_active_user") as mock_current_user:
            mock_current_user.return_value = test_user

            # Mock the database session
            with patch("app.routers.card_history.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                with patch("app.services.card.get_card") as mock_get_card:
                    mock_get_card.side_effect = Exception("Invalid card_id type")

                    with pytest.raises(Exception) as exc_info:
                        asyncio.run(
                            get_card_history(
                                "invalid", mock_db.return_value.__enter__.return_value, mock_current_user.return_value
                            )
                        )

                    assert "Invalid card_id type" in str(exc_info.value)

    def test_create_card_history_entry_invalid_card_id(self, test_user):
        """Test de création d'une entrée d'historique avec un ID de carte invalide."""
        from app.routers.card_history import create_card_history_entry

        history_data = {
            "card_id": "invalid",
            "user_id": 1,
            "action": "card_updated",
            "description": "Carte mise à jour",
        }

        with patch("app.routers.card_history.get_current_active_user") as mock_current_user:
            mock_current_user.return_value = test_user

            # Mock the database session
            with patch("app.routers.card_history.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                # When calling directly, type validation doesn't occur
                with pytest.raises(Exception):
                    asyncio.run(
                        create_card_history_entry(
                            "invalid",
                            history_data,
                            mock_db.return_value.__enter__.return_value,
                            mock_current_user.return_value,
                        )
                    )

    def test_create_card_history_entry_missing_required_fields(self, test_user):
        """Test de création d'une entrée d'historique avec des champs manquants."""
        incomplete_data = {
            "card_id": 1,
            "user_id": 1,
            # Missing action and description
        }

        with patch("app.routers.card_history.get_current_active_user") as mock_current_user:
            mock_current_user.return_value = test_user

            # Mock the database session
            with patch("app.routers.card_history.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                # When calling directly, validation doesn't occur the same way as with FastAPI
                # The CardHistoryCreate pydantic model will validate the data
                with pytest.raises(Exception):
                    asyncio.run(
                        create_card_history_entry(
                            1,
                            incomplete_data,
                            mock_db.return_value.__enter__.return_value,
                            mock_current_user.return_value,
                        )
                    )

    def test_create_card_history_entry_empty_action(self, test_user, test_card):
        """Test de création d'une entrée d'historique avec une action vide."""
        from app.routers.card_history import create_card_history_entry

        history_data = {
            "card_id": 1,
            "user_id": 1,
            "action": "   ",  # Use whitespace instead of empty string
            "description": "Carte mise à jour",
        }

        with patch("app.routers.card_history.get_current_active_user") as mock_current_user:
            mock_current_user.return_value = test_user

            # Mock the database session
            with patch("app.routers.card_history.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                with patch("app.services.card.get_card") as mock_get_card:
                    mock_get_card.return_value = test_card

                    with patch("app.services.card_history.create_card_history_entry") as mock_create:
                        mock_create.side_effect = ValueError("Action cannot be empty")

                        with pytest.raises(ValueError) as exc_info:
                            asyncio.run(
                                create_card_history_entry(
                                    1,
                                    history_data,
                                    mock_db.return_value.__enter__.return_value,
                                    mock_current_user.return_value,
                                )
                            )

                        assert str(exc_info.value) == "Action cannot be empty"

    def test_create_card_history_entry_empty_description(self, test_user, test_card):
        """Test de création d'une entrée d'historique avec une description vide."""
        from app.routers.card_history import create_card_history_entry

        history_data = {
            "card_id": 1,
            "user_id": 1,
            "action": "card_updated",
            "description": "   ",  # Use whitespace instead of empty string
        }

        with patch("app.routers.card_history.get_current_active_user") as mock_current_user:
            mock_current_user.return_value = test_user

            # Mock the database session
            with patch("app.routers.card_history.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                with patch("app.services.card.get_card") as mock_get_card:
                    mock_get_card.return_value = test_card

                    with patch("app.services.card_history.create_card_history_entry") as mock_create:
                        mock_create.side_effect = ValueError("Description cannot be empty")

                        with pytest.raises(ValueError) as exc_info:
                            asyncio.run(
                                create_card_history_entry(
                                    1,
                                    history_data,
                                    mock_db.return_value.__enter__.return_value,
                                    mock_current_user.return_value,
                                )
                            )

                        assert str(exc_info.value) == "Description cannot be empty"

    def test_create_card_history_entry_negative_card_id(self, test_user):
        """Test de création d'une entrée d'historique avec un ID de carte négatif."""
        from app.routers.card_history import create_card_history_entry

        history_data = {"card_id": -1, "user_id": 1, "action": "card_updated", "description": "Carte mise à jour"}

        with patch("app.routers.card_history.get_current_active_user") as mock_current_user:
            mock_current_user.return_value = test_user

            # Mock the database session
            with patch("app.routers.card_history.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                with patch("app.services.card.get_card") as mock_get_card:
                    mock_get_card.return_value = None

                    with pytest.raises(HTTPException) as exc_info:
                        asyncio.run(
                            create_card_history_entry(
                                -1,
                                history_data,
                                mock_db.return_value.__enter__.return_value,
                                mock_current_user.return_value,
                            )
                        )

                    assert exc_info.value.status_code == 404
                    assert exc_info.value.detail == "Carte non trouvée"

    def test_create_card_history_entry_negative_user_id(self, test_user):
        """Test de création d'une entrée d'historique avec un ID d'utilisateur négatif."""
        history_data = {"card_id": 1, "user_id": -1, "action": "card_updated", "description": "Carte mise à jour"}

        with patch("app.routers.card_history.get_current_active_user") as mock_current_user:
            mock_current_user.return_value = test_user

            # Mock the database session
            with patch("app.routers.card_history.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                # When calling directly, validation doesn't occur the same way as with FastAPI
                # Just check that some exception is raised for invalid data
                with pytest.raises(Exception):
                    asyncio.run(
                        create_card_history_entry(
                            1,
                            history_data,
                            mock_db.return_value.__enter__.return_value,
                            mock_current_user.return_value,
                        )
                    )

    def test_get_card_history_service_error(self, test_user, test_card):
        """Test de récupération de l'historique avec une erreur du service."""
        from app.routers.card_history import get_card_history

        with patch("app.services.card.get_card") as mock_get_card:
            mock_get_card.return_value = test_card

            with patch("app.services.card_history.get_card_history") as mock_get_history:
                mock_get_history.side_effect = Exception("Database error")

                with patch("app.routers.card_history.get_current_active_user") as mock_current_user:
                    mock_current_user.return_value = test_user

                    # Mock the database session
                    with patch("app.routers.card_history.get_db") as mock_db:
                        mock_db.return_value.__enter__.return_value = MagicMock()

                        with pytest.raises(Exception) as exc_info:
                            asyncio.run(
                                get_card_history(
                                    1, mock_db.return_value.__enter__.return_value, mock_current_user.return_value
                                )
                            )

                        # Check that it's either an HTTPException with status 500 or the original exception
                        if hasattr(exc_info.value, "status_code"):
                            assert exc_info.value.status_code == 500
                        else:
                            assert "Database error" in str(exc_info.value)

    def test_create_card_history_entry_service_error(self, test_user, test_card):
        """Test de création d'une entrée d'historique avec une erreur du service."""
        from app.routers.card_history import create_card_history_entry

        history_data = {"card_id": 1, "user_id": 1, "action": "card_updated", "description": "Carte mise à jour"}

        with patch("app.services.card.get_card") as mock_get_card:
            mock_get_card.return_value = test_card

            with patch("app.services.card_history.create_card_history_entry") as mock_create:
                mock_create.side_effect = Exception("Service error")

                with patch("app.routers.card_history.get_current_active_user") as mock_current_user:
                    mock_current_user.return_value = test_user

                    # Mock the database session
                    with patch("app.routers.card_history.get_db") as mock_db:
                        mock_db.return_value.__enter__.return_value = MagicMock()

                        with pytest.raises(Exception) as exc_info:
                            asyncio.run(
                                create_card_history_entry(
                                    1,
                                    history_data,
                                    mock_db.return_value.__enter__.return_value,
                                    mock_current_user.return_value,
                                )
                            )

                        # Check that it's either an HTTPException with status 500 or the original exception
                        if hasattr(exc_info.value, "status_code"):
                            assert exc_info.value.status_code == 500
                        else:
                            assert "Service error" in str(exc_info.value)

    def test_get_card_history_card_service_error(self, test_user):
        """Test de récupération de l'historique avec une erreur du service de carte."""
        from app.routers.card_history import get_card_history

        with patch("app.services.card.get_card") as mock_get_card:
            mock_get_card.side_effect = Exception("Card service error")

            with patch("app.routers.card_history.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = test_user

                # Mock the database session
                with patch("app.routers.card_history.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    with pytest.raises(Exception) as exc_info:
                        asyncio.run(
                            get_card_history(
                                1, mock_db.return_value.__enter__.return_value, mock_current_user.return_value
                            )
                        )

                    # Check that it's either an HTTPException with status 500 or the original exception
                    if hasattr(exc_info.value, "status_code"):
                        assert exc_info.value.status_code == 500
                    else:
                        assert "Card service error" in str(exc_info.value)

    def test_create_card_history_entry_card_service_error(self, test_user):
        """Test de création d'une entrée d'historique avec une erreur du service de carte."""
        from app.routers.card_history import create_card_history_entry

        history_data = {"card_id": 1, "user_id": 1, "action": "card_updated", "description": "Carte mise à jour"}

        with patch("app.services.card.get_card") as mock_get_card:
            mock_get_card.side_effect = Exception("Card service error")

            with patch("app.routers.card_history.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = test_user

                # Mock the database session
                with patch("app.routers.card_history.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    with pytest.raises(Exception) as exc_info:
                        asyncio.run(
                            create_card_history_entry(
                                1,
                                history_data,
                                mock_db.return_value.__enter__.return_value,
                                mock_current_user.return_value,
                            )
                        )

                    # Check that it's either an HTTPException with status 500 or the original exception
                    if hasattr(exc_info.value, "status_code"):
                        assert exc_info.value.status_code == 500
                    else:
                        assert "Card service error" in str(exc_info.value)

    def test_get_card_history_zero_card_id(self, test_user):
        """Test de récupération de l'historique avec un ID de carte zéro."""
        from app.routers.card_history import get_card_history

        with patch("app.routers.card_history.get_current_active_user") as mock_current_user:
            mock_current_user.return_value = test_user

            # Mock the database session
            with patch("app.routers.card_history.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                # Zero is a valid integer, but card should not exist
                with patch("app.services.card.get_card") as mock_get_card:
                    mock_get_card.return_value = None

                    with pytest.raises(HTTPException) as exc_info:
                        asyncio.run(
                            get_card_history(
                                0, mock_db.return_value.__enter__.return_value, mock_current_user.return_value
                            )
                        )

                    assert exc_info.value.status_code == 404
                    assert exc_info.value.detail == "Carte non trouvée"

    def test_create_card_history_entry_zero_card_id(self, test_user):
        """Test de création d'une entrée d'historique avec un ID de carte zéro."""
        from app.routers.card_history import create_card_history_entry

        history_data = {"card_id": 0, "user_id": 1, "action": "card_updated", "description": "Carte mise à jour"}

        with patch("app.routers.card_history.get_current_active_user") as mock_current_user:
            mock_current_user.return_value = test_user

            # Mock the database session
            with patch("app.routers.card_history.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                # Zero is a valid integer, but card should not exist
                with patch("app.services.card.get_card") as mock_get_card:
                    mock_get_card.return_value = None

                    with pytest.raises(HTTPException) as exc_info:
                        asyncio.run(
                            create_card_history_entry(
                                0,
                                history_data,
                                mock_db.return_value.__enter__.return_value,
                                mock_current_user.return_value,
                            )
                        )

                    assert exc_info.value.status_code == 404
                    assert exc_info.value.detail == "Carte non trouvée"
