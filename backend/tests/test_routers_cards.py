"""Tests pour le routeur cards."""

import asyncio
import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, Query, status

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base
from app.models.card import Card, CardPriority
from app.models.user import User, UserRole, UserStatus
from app.routers.cards import (
    archive_card,
    bulk_move_cards,
    create_card,
    delete_card,
    get_card_history,
    move_card,
    read_archived_cards,
    read_card,
    read_cards,
    unarchive_card,
    update_card,
)
from app.schemas import (
    BulkCardMoveRequest,
    CardCreate,
    CardFilter,
    CardHistoryCreate,
    CardHistoryResponse,
    CardListUpdate,
    CardMoveRequest,
    CardResponse,
    CardUpdate,
)
from app.services.card import archive_card as service_archive_card
from app.services.card import bulk_move_cards as service_bulk_move_cards
from app.services.card import create_card as service_create_card
from app.services.card import delete_card as service_delete_card
from app.services.card import get_archived_cards, get_card, get_cards
from app.services.card import move_card as service_move_card
from app.services.card import unarchive_card as service_unarchive_card
from app.services.card import update_card as service_update_card
from app.services.card import update_card_list
from app.services.card_history import create_card_history_entry as service_create_history
from app.services.card_history import get_card_history as service_get_card_history
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
    """Fixture pour créer un utilisateur de test avec rôle SUPERVISOR pour tester la logique métier."""
    user = User(
        email="test@example.com",
        display_name="Test User",
        password_hash="$2b$12$testhashedpassword",
        role=UserRole.SUPERVISOR,
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
        priority=CardPriority.MEDIUM,
        is_archived=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(card)
    db_session.commit()
    db_session.refresh(card)
    return card


class TestCardsRouter:
    """Tests pour le routeur des cartes."""

    def test_list_cards_success(self, test_user):
        """Test de récupération des cartes avec succès."""
        with patch("app.services.card.get_cards") as mock_get_cards:
            mock_cards = [
                CardResponse(
                    id=1,
                    title="Test Card",
                    description="Test description",
                    list_id=1,
                    position=0,
                    priority=CardPriority.MEDIUM,
                    is_archived=False,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    created_by=1,
                    assignee_id=None,
                )
            ]
            mock_get_cards.return_value = mock_cards

            with patch("app.routers.cards.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = test_user

                # Mock database session
                with patch("app.routers.cards.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    result = asyncio.run(
                        read_cards(
                            skip=0,
                            limit=10,
                            list_id=1,
                            statut=None,
                            assignee_id=None,
                            priority=None,
                            label_id=None,
                            search=None,
                            include_archived=False,
                            db=mock_db.return_value.__enter__.return_value,
                            current_user=test_user,
                        )
                    )

                    assert len(result) == 1
                    assert result[0].title == "Test Card"

    def test_list_cards_with_filters(self, test_user):
        """Test de récupération des cartes avec filtres."""
        with patch("app.services.card.get_cards") as mock_get_cards:
            mock_cards = [
                CardResponse(
                    id=1,
                    title="High Priority Card",
                    description="Important task",
                    list_id=1,
                    position=0,
                    priority=CardPriority.HIGH,
                    is_archived=False,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    created_by=1,
                    assignee_id=None,
                )
            ]
            mock_get_cards.return_value = mock_cards

            with patch("app.routers.cards.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = test_user

                # Mock database session
                with patch("app.routers.cards.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    result = asyncio.run(
                        read_cards(
                            list_id=1,
                            skip=0,
                            limit=10,
                            search="High",
                            priority=CardPriority.HIGH,
                            assignee_id=None,
                            label_id=None,
                            include_archived=False,
                            statut=None,
                            db=mock_db.return_value.__enter__.return_value,
                            current_user=test_user,
                        )
                    )

                    assert len(result) == 1
                    assert result[0].priority == CardPriority.HIGH

    def test_list_archived_cards_success(self, test_user):
        """Test de récupération des cartes archivées avec succès."""
        with patch("app.services.card.get_archived_cards") as mock_get_archived:
            mock_cards = [
                CardResponse(
                    id=1,
                    title="Archived Card",
                    description="Old task",
                    list_id=1,
                    position=0,
                    priority=CardPriority.LOW,
                    is_archived=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    created_by=1,
                    assignee_id=None,
                )
            ]
            mock_get_archived.return_value = mock_cards

            with patch("app.routers.cards.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = test_user

                # Mock database session
                with patch("app.routers.cards.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    result = asyncio.run(
                        read_archived_cards(
                            skip=0, limit=10, db=mock_db.return_value.__enter__.return_value, current_user=test_user
                        )
                    )

                    assert len(result) == 1
                    assert result[0].is_archived is True

    def test_create_card_success(self, test_user):
        """Test de création d'une carte avec succès."""
        card_data = CardCreate(
            title="New Card", description="New description", list_id=1, priority=CardPriority.MEDIUM
        )

        mock_card = CardResponse(
            id=1,
            title="New Card",
            description="New description",
            list_id=1,
            position=0,
            priority=CardPriority.MEDIUM,
            is_archived=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            created_by=1,
            assignee_id=None,
        )

        with patch("app.services.card.create_card") as mock_create:
            mock_create.return_value = mock_card

            with patch("app.services.card_history.create_card_history_entry") as mock_history:
                mock_history.return_value = None

                with patch("app.routers.cards.get_current_active_user") as mock_current_user:
                    mock_current_user.return_value = test_user

                    # Mock database session
                    with patch("app.routers.cards.get_db") as mock_db:
                        mock_db.return_value.__enter__.return_value = MagicMock()

                        result = asyncio.run(
                            create_card(card_data, mock_db.return_value.__enter__.return_value, test_user)
                        )

                        assert result.title == "New Card"
                        assert result.description == "New description"
                        assert result.priority == CardPriority.MEDIUM

    def test_create_card_invalid_data(self, test_user):
        """Test de création d'une carte avec des données invalides."""
        # Créer un objet CardCreate valide
        card_data = CardCreate(
            title="Test Card", description="Test description", list_id=1, priority=CardPriority.MEDIUM
        )

        with patch("app.services.card.create_card") as mock_create:
            # Simuler une erreur du service (par exemple, liste inexistante)
            mock_create.side_effect = ValueError("Liste non trouvée")

            with patch("app.routers.cards.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = test_user

                # Mock database session
                with patch("app.routers.cards.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    with pytest.raises(HTTPException) as exc_info:
                        asyncio.run(create_card(card_data, mock_db.return_value.__enter__.return_value, test_user))

                    assert exc_info.value.status_code == 400
                    assert exc_info.value.detail == "Liste non trouvée"

    def test_create_card_empty_title(self, test_user):
        """Test de validation Pydantic pour un title vide."""
        # Tester que Pydantic rejette les données invalides
        with pytest.raises(Exception) as exc_info:
            CardCreate(title="", description="New description", list_id=1, priority=CardPriority.MEDIUM)

        # Vérifier que c'est bien une erreur de validation Pydantic
        assert "title" in str(exc_info.value)
        assert "String should have at least 1 character" in str(exc_info.value)

    def test_get_card_success(self, test_user, test_card):
        """Test de récupération d'une carte spécifique avec succès."""
        with patch("app.services.card.get_card") as mock_get_card:
            mock_card = CardResponse(
                id=1,
                title="Test Card",
                description="Test description",
                list_id=1,
                position=0,
                priority=CardPriority.MEDIUM,
                is_archived=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                created_by=1,
                assignee_id=None,
            )
            mock_get_card.return_value = mock_card

            with patch("app.routers.cards.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = test_user

                # Mock database session
                with patch("app.routers.cards.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    result = asyncio.run(read_card(1, mock_db.return_value.__enter__.return_value, test_user))

                    assert result.title == "Test Card"
                    assert result.id == 1

    def test_get_card_not_found(self, test_user):
        """Test de récupération d'une carte qui n'existe pas."""
        with patch("app.services.card.get_card") as mock_get_card:
            mock_get_card.return_value = None

            with patch("app.routers.cards.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = test_user

                # Mock database session
                with patch("app.routers.cards.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    with pytest.raises(HTTPException) as exc_info:
                        asyncio.run(read_card(999, mock_db.return_value.__enter__.return_value, test_user))

                    assert exc_info.value.status_code == 404
                    assert exc_info.value.detail == "Carte non trouvée"

    def test_update_card_success(self, test_user):
        """Test de mise à jour d'une carte avec succès."""
        update_data = CardUpdate(title="Updated Card", description="Updated description", priority=CardPriority.HIGH)

        mock_card = CardResponse(
            id=1,
            title="Updated Card",
            description="Updated description",
            list_id=1,
            position=0,
            priority=CardPriority.HIGH,
            is_archived=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            created_by=1,
            assignee_id=None,
        )

        with patch("app.services.card.update_card") as mock_update:
            mock_update.return_value = mock_card

            with patch("app.services.card_history.create_card_history_entry") as mock_history:
                mock_history.return_value = None

                with patch("app.routers.cards.get_current_active_user") as mock_current_user:
                    mock_current_user.return_value = test_user

                    # Mock database session
                    with patch("app.routers.cards.get_db") as mock_db:
                        mock_db.return_value.__enter__.return_value = MagicMock()

                        result = asyncio.run(
                            update_card(1, update_data, mock_db.return_value.__enter__.return_value, test_user)
                        )

                        assert result.title == "Updated Card"
                        assert result.priority == CardPriority.HIGH

    def test_update_card_not_found(self, test_user):
        """Test de mise à jour d'une carte qui n'existe pas."""
        update_data = CardUpdate(title="Updated Card")

        with patch("app.services.card.update_card") as mock_update:
            mock_update.return_value = None

            with patch("app.routers.cards.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = test_user

                # Mock database session
                with patch("app.routers.cards.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    with pytest.raises(HTTPException) as exc_info:
                        asyncio.run(
                            update_card(999, update_data, mock_db.return_value.__enter__.return_value, test_user)
                        )

                    assert exc_info.value.status_code == 404
                    assert exc_info.value.detail == "Carte non trouvée"

    def test_archive_card_success(self, test_user):
        """Test d'archivage d'une carte avec succès."""
        mock_card = CardResponse(
            id=1,
            title="Test Card",
            description="Test description",
            list_id=1,
            position=0,
            priority=CardPriority.MEDIUM,
            is_archived=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            created_by=1,
            assignee_id=None,
        )

        with patch("app.services.card.archive_card") as mock_archive:
            mock_archive.return_value = mock_card

            with patch("app.services.card_history.create_card_history_entry") as mock_history:
                mock_history.return_value = None

                with patch("app.routers.cards.get_current_active_user") as mock_current_user:
                    mock_current_user.return_value = test_user

                    # Mock database session
                    with patch("app.routers.cards.get_db") as mock_db:
                        mock_db.return_value.__enter__.return_value = MagicMock()

                        result = asyncio.run(archive_card(1, mock_db.return_value.__enter__.return_value, test_user))

                        assert result.is_archived is True

    def test_archive_card_not_found(self, test_user):
        """Test d'archivage d'une carte qui n'existe pas."""
        with patch("app.services.card.archive_card") as mock_archive:
            mock_archive.return_value = None

            with patch("app.routers.cards.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = test_user

                # Mock database session
                with patch("app.routers.cards.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    with pytest.raises(HTTPException) as exc_info:
                        asyncio.run(archive_card(999, mock_db.return_value.__enter__.return_value, test_user))

                    assert exc_info.value.status_code == 404
                    assert exc_info.value.detail == "Carte non trouvée"

    def test_unarchive_card_success(self, test_user):
        """Test de désarchivage d'une carte avec succès."""
        mock_card = CardResponse(
            id=1,
            title="Test Card",
            description="Test description",
            list_id=1,
            position=0,
            priority=CardPriority.MEDIUM,
            is_archived=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            created_by=1,
            assignee_id=None,
        )

        with patch("app.services.card.unarchive_card") as mock_unarchive:
            mock_unarchive.return_value = mock_card

            with patch("app.services.card_history.create_card_history_entry") as mock_history:
                mock_history.return_value = None

                with patch("app.routers.cards.get_current_active_user") as mock_current_user:
                    mock_current_user.return_value = test_user

                    # Mock database session
                    with patch("app.routers.cards.get_db") as mock_db:
                        mock_db.return_value.__enter__.return_value = MagicMock()

                        result = asyncio.run(unarchive_card(1, mock_db.return_value.__enter__.return_value, test_user))

                        assert result.is_archived is False

    def test_move_card_success(self, test_user):
        """Test de déplacement d'une carte avec succès."""
        move_data = CardMoveRequest(source_list_id=1, target_list_id=2, position=0)

        mock_card = CardResponse(
            id=1,
            title="Test Card",
            description="Test description",
            list_id=2,
            position=0,
            priority=CardPriority.MEDIUM,
            is_archived=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            created_by=1,
            assignee_id=None,
        )

        with patch("app.services.card.move_card") as mock_move:
            mock_move.return_value = mock_card

            with patch("app.services.card_history.create_card_history_entry") as mock_history:
                mock_history.return_value = None

                with patch("app.routers.cards.get_current_active_user") as mock_current_user:
                    mock_current_user.return_value = test_user

                    # Mock database session
                    with patch("app.routers.cards.get_db") as mock_db:
                        mock_db.return_value.__enter__.return_value = MagicMock()

                        result = asyncio.run(
                            move_card(1, move_data, mock_db.return_value.__enter__.return_value, test_user)
                        )

                        assert result.list_id == 2

    def test_bulk_move_cards_success(self, test_user):
        """Test de déplacement en masse de cartes avec succès."""
        move_data = BulkCardMoveRequest(card_ids=[1, 2, 3], target_list_id=2)

        mock_cards = [
            CardResponse(
                id=1,
                title="Card 1",
                description="Description 1",
                list_id=2,
                position=0,
                priority=CardPriority.MEDIUM,
                is_archived=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                created_by=1,
                assignee_id=None,
            )
        ]

        with patch("app.services.card.bulk_move_cards") as mock_bulk_move:
            mock_bulk_move.return_value = mock_cards

            with patch("app.services.card_history.create_card_history_entry") as mock_history:
                mock_history.return_value = None

                with patch("app.routers.cards.get_current_active_user") as mock_current_user:
                    mock_current_user.return_value = test_user

                    # Mock database session
                    with patch("app.routers.cards.get_db") as mock_db:
                        mock_db.return_value.__enter__.return_value = MagicMock()

                        result = asyncio.run(
                            bulk_move_cards(move_data, mock_db.return_value.__enter__.return_value, test_user)
                        )

                        assert len(result) == 1
                        assert result[0].list_id == 2

    def test_delete_card_success(self, test_user):
        """Test de suppression d'une carte avec succès."""
        with patch("app.services.card.delete_card") as mock_delete:
            mock_delete.return_value = True

            with patch("app.services.card_history.create_card_history_entry") as mock_history:
                mock_history.return_value = None

                with patch("app.routers.cards.get_current_active_user") as mock_current_user:
                    mock_current_user.return_value = test_user

                    # Mock database session
                    with patch("app.routers.cards.get_db") as mock_db:
                        mock_db.return_value.__enter__.return_value = MagicMock()

                        result = asyncio.run(delete_card(1, mock_db.return_value.__enter__.return_value, test_user))

                        assert result["message"] == "Carte supprimée avec succès"

    def test_delete_card_not_found(self, test_user):
        """Test de suppression d'une carte qui n'existe pas."""
        with patch("app.services.card.delete_card") as mock_delete:
            mock_delete.return_value = False

            with patch("app.routers.cards.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = test_user

                # Mock database session
                with patch("app.routers.cards.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    with pytest.raises(HTTPException) as exc_info:
                        asyncio.run(delete_card(999, mock_db.return_value.__enter__.return_value, test_user))

                    assert exc_info.value.status_code == 404
                    assert exc_info.value.detail == "Carte non trouvée"

    def test_get_card_history_success(self, test_user):
        """Test de récupération de l'historique d'une carte avec succès."""
        with patch("app.services.card_history.get_card_history") as mock_get_history:
            mock_history = [
                CardHistoryResponse(
                    id=1,
                    card_id=1,
                    user_id=1,
                    action="created",
                    description="Card created: New Card",
                    created_at=datetime.utcnow(),
                )
            ]
            mock_get_history.return_value = mock_history

            with patch("app.routers.cards.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = test_user

                # Mock database session
                with patch("app.routers.cards.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    result = asyncio.run(get_card_history(1, mock_db.return_value.__enter__.return_value, test_user))

                    assert len(result) == 1
                    assert result[0].action == "created"

    def test_invalid_card_id(self, test_user):
        """Test avec un ID de carte négatif (invalide mais du bon type)."""
        with patch("app.services.card.get_card") as mock_get_card:
            # Simuler que le service renvoie None pour un ID invalide
            mock_get_card.return_value = None

            with patch("app.routers.cards.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = test_user

                # Mock database session
                with patch("app.routers.cards.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                with pytest.raises(HTTPException) as exc_info:
                    asyncio.run(read_card(-1, mock_db.return_value.__enter__.return_value, test_user))

                assert exc_info.value.status_code == 404
                assert exc_info.value.detail == "Carte non trouvée"

    def test_service_error_handling(self, test_user):
        """Test de gestion des erreurs de service."""
        with patch("app.services.card.get_cards") as mock_get_cards:
            mock_get_cards.side_effect = Exception("Database error")

            with patch("app.routers.cards.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = test_user

                # Mock database session
                with patch("app.routers.cards.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    # Le routeur ne gère pas les exceptions, donc l'exception devrait se propager
                    with pytest.raises(Exception) as exc_info:
                        asyncio.run(
                            read_cards(
                                list_id=1,
                                skip=0,
                                limit=10,
                                search=None,
                                priority=None,
                                assignee_id=None,
                                label_id=None,
                                include_archived=False,
                                statut=None,
                                db=mock_db.return_value.__enter__.return_value,
                                current_user=test_user,
                            )
                        )

                    assert "Database error" in str(exc_info.value)


# Import needed for tests
import asyncio
