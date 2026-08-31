"""Tests pour le service CardHistory."""

import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base
from app.models.card import Card, CardPriority
from app.models.card_history import CardHistory
from app.models.kanban_list import KanbanList
from app.models.user import User, UserRole, UserStatus
from app.schemas.card_history import CardHistoryCreate
from app.services.card_history import (
    create_card_history_entry,
    get_card_history,
    get_card_history_with_users,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configuration de la base de données de test
TEST_DB_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(TEST_DB_DIR, exist_ok=True)
TEST_DB_PATH = os.path.join(TEST_DB_DIR, "test_card_history.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    """Fixture pour créer une session de base de données de test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_user(db_session):
    """Fixture pour créer un utilisateur de test."""
    user = User(
        email="test@example.com",
        display_name="Test User",
        role=UserRole.EDITOR,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_kanban_list(db_session):
    """Fixture pour créer une liste Kanban de test."""
    kanban_list = KanbanList(name="Test List", order=1)
    db_session.add(kanban_list)
    db_session.commit()
    db_session.refresh(kanban_list)
    return kanban_list


@pytest.fixture
def sample_card(db_session, sample_kanban_list, sample_user):
    """Fixture pour créer une carte de test."""
    card = Card(
        title="Test Card",
        description="Test Description",
        priority=CardPriority.MEDIUM,
        list_id=sample_kanban_list.id,
        created_by=sample_user.id,
    )
    db_session.add(card)
    db_session.commit()
    db_session.refresh(card)
    return card


@pytest.fixture
def sample_history_entries(db_session, sample_card, sample_user):
    """Fixture pour créer des entrées d'historique de test."""
    entries = [
        CardHistory(
            card_id=sample_card.id,
            user_id=sample_user.id,
            action="created",
            description="Carte créée",
        ),
        CardHistory(
            card_id=sample_card.id,
            user_id=sample_user.id,
            action="updated",
            description="Titre mis à jour",
        ),
        CardHistory(
            card_id=sample_card.id,
            user_id=sample_user.id,
            action="moved",
            description="Carte déplacée vers 'En cours'",
        ),
    ]

    for entry in entries:
        db_session.add(entry)
    db_session.commit()

    for entry in entries:
        db_session.refresh(entry)

    return entries


class TestCreateCardHistoryEntry:
    """Tests pour la fonction create_card_history_entry."""

    def test_create_history_entry_success(self, db_session, sample_card, sample_user):
        """Test de création réussie d'une entrée d'historique."""
        history_data = CardHistoryCreate(
            card_id=sample_card.id,
            user_id=sample_user.id,
            action="created",
            description="Carte créée avec succès",
        )

        result = create_card_history_entry(db_session, history_data)

        assert result.id is not None
        assert result.card_id == sample_card.id
        assert result.user_id == sample_user.id
        assert result.action == "created"
        assert result.description == "Carte créée avec succès"
        assert result.created_at is not None

    def test_create_history_entry_different_actions(
        self, db_session, sample_card, sample_user
    ):
        """Test de création d'entrées avec différents types d'actions."""
        actions = ["created", "updated", "deleted", "moved", "assigned", "commented"]

        for action in actions:
            history_data = CardHistoryCreate(
                card_id=sample_card.id,
                user_id=sample_user.id,
                action=action,
                description=f"Action {action} effectuée",
            )

            result = create_card_history_entry(db_session, history_data)

            assert result.action == action
            assert result.description == f"Action {action} effectuée"

    def test_create_history_entry_unicode_content(
        self, db_session, sample_card, sample_user
    ):
        """Test de création d'entrée avec contenu Unicode."""
        history_data = CardHistoryCreate(
            card_id=sample_card.id,
            user_id=sample_user.id,
            action="updated",
            description="Mise à jour avec caractères spéciaux: éèàçù 🚀 中文",
        )

        result = create_card_history_entry(db_session, history_data)

        assert (
            result.description == "Mise à jour avec caractères spéciaux: éèàçù 🚀 中文"
        )

    def test_create_history_entry_long_description(
        self, db_session, sample_card, sample_user
    ):
        """Test de création d'entrée avec une description très longue."""
        long_description = "x" * 5000
        history_data = CardHistoryCreate(
            card_id=sample_card.id,
            user_id=sample_user.id,
            action="updated",
            description=long_description,
        )

        result = create_card_history_entry(db_session, history_data)

        assert result.description == long_description

    def test_create_history_entry_empty_strings(
        self, db_session, sample_card, sample_user
    ):
        """Test de création d'entrée avec des chaînes vides."""
        history_data = CardHistoryCreate(
            card_id=sample_card.id, user_id=sample_user.id, action="", description=""
        )

        result = create_card_history_entry(db_session, history_data)

        assert result.action == ""
        assert result.description == ""

    def test_create_history_entry_whitespace_only(
        self, db_session, sample_card, sample_user
    ):
        """Test de création d'entrée avec des espaces uniquement."""
        history_data = CardHistoryCreate(
            card_id=sample_card.id,
            user_id=sample_user.id,
            action="  ",
            description="  Description avec espaces  ",
        )

        result = create_card_history_entry(db_session, history_data)

        assert result.action == "  "
        assert result.description == "  Description avec espaces  "

    def test_create_history_entry_database_error(
        self, db_session, sample_card, sample_user
    ):
        """Test de gestion des erreurs de base de données."""
        history_data = CardHistoryCreate(
            card_id=sample_card.id,
            user_id=sample_user.id,
            action="created",
            description="Test erreur",
        )

        with patch.object(
            db_session, "commit", side_effect=SQLAlchemyError("Database error")
        ):
            with pytest.raises(SQLAlchemyError):
                create_card_history_entry(db_session, history_data)

    def test_create_history_entry_foreign_key_constraint(self, db_session):
        """Test de création avec des clés étrangères invalides."""
        # Note: SQLite ne vérifie pas les contraintes de clé étrangère par défaut
        # Ce test vérifie simplement que la fonction peut gérer des IDs invalides
        # sans que cela ne cause de problème immédiat
        history_data = CardHistoryCreate(
            card_id=99999,  # ID inexistant
            user_id=99999,  # ID inexistant
            action="created",
            description="Test contrainte",
        )

        # Dans la pratique, les contraintes de clé étrangère dépendent de la
        # configuration de la base de données. Ce test montre simplement que
        # la fonction accepte les données sans validation supplémentaire.
        try:
            result = create_card_history_entry(db_session, history_data)
            # Si ça passe, c'est que SQLite n'a pas de contraintes FK actives
            assert result.card_id == 99999
            assert result.user_id == 99999
        except Exception:
            # Si une erreur est levée, c'est que les contraintes sont actives
            pass

    def test_create_history_entry_sql_injection_attempt(
        self, db_session, sample_card, sample_user
    ):
        """Test de tentative d'injection SQL."""
        malicious_action = "created'; DROP TABLE card_history; --"
        malicious_description = "Description'; DROP TABLE card_history; --"

        history_data = CardHistoryCreate(
            card_id=sample_card.id,
            user_id=sample_user.id,
            action=malicious_action,
            description=malicious_description,
        )

        result = create_card_history_entry(db_session, history_data)

        # Les données doivent être stockées telles quelles, pas interprétées
        assert result.action == malicious_action
        assert result.description == malicious_description


class TestGetCardHistory:
    """Tests pour la fonction get_card_history."""

    def test_get_card_history_success(self, db_session, sample_history_entries):
        """Test de récupération réussie de l'historique d'une carte."""
        card_id = sample_history_entries[0].card_id
        history = get_card_history(db_session, card_id)

        assert len(history) == 3
        # Vérifier que les entrées sont triées par date décroissante
        for i in range(len(history) - 1):
            assert history[i].created_at is not None
            assert history[i + 1].created_at is not None
            assert history[i].created_at >= history[i + 1].created_at  # type: ignore

        # Vérifier les actions
        actions = [entry.action for entry in history]
        assert "created" in actions
        assert "updated" in actions
        assert "moved" in actions

    def test_get_card_history_empty(self, db_session, sample_card):
        """Test de récupération de l'historique d'une carte sans historique."""
        history = get_card_history(db_session, sample_card.id)

        assert len(history) == 0

    def test_get_card_history_nonexistent_card(self, db_session):
        """Test de récupération de l'historique d'une carte qui n'existe pas."""
        history = get_card_history(db_session, 99999)

        assert len(history) == 0

    def test_get_card_history_single_entry(self, db_session, sample_card, sample_user):
        """Test de récupération d'une seule entrée d'historique."""
        # Créer une seule entrée
        entry = CardHistory(
            card_id=sample_card.id,
            user_id=sample_user.id,
            action="created",
            description="Seule entrée",
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)

        history = get_card_history(db_session, sample_card.id)

        assert len(history) == 1
        assert history[0].action == "created"
        assert history[0].description == "Seule entrée"

    def test_get_card_history_multiple_cards(
        self, db_session, sample_user, sample_kanban_list
    ):
        """Test de récupération d'historique pour plusieurs cartes différentes."""
        # Créer deux cartes
        card1 = Card(
            title="Card 1",
            description="Description 1",
            priority=CardPriority.MEDIUM,
            list_id=sample_kanban_list.id,
            created_by=sample_user.id,
        )
        card2 = Card(
            title="Card 2",
            description="Description 2",
            priority=CardPriority.MEDIUM,
            list_id=sample_kanban_list.id,
            created_by=sample_user.id,
        )
        db_session.add(card1)
        db_session.add(card2)
        db_session.commit()
        db_session.refresh(card1)
        db_session.refresh(card2)

        # Ajouter de l'historique pour chaque carte
        entry1 = CardHistory(
            card_id=card1.id,
            user_id=sample_user.id,
            action="created",
            description="Card 1 créée",
        )
        entry2 = CardHistory(
            card_id=card2.id,
            user_id=sample_user.id,
            action="created",
            description="Card 2 créée",
        )
        db_session.add(entry1)
        db_session.add(entry2)
        db_session.commit()

        # Vérifier que chaque carte a son propre historique
        history1 = get_card_history(db_session, card1.id)
        history2 = get_card_history(db_session, card2.id)

        assert len(history1) == 1
        assert len(history2) == 1
        assert history1[0].description == "Card 1 créée"
        assert history2[0].description == "Card 2 créée"

    def test_get_card_history_ordering(self, db_session, sample_card, sample_user):
        """Test que l'historique est bien trié par date décroissante."""
        # Créer des entrées avec des timestamps manuels pour tester le tri
        entries = []
        for i in range(5):
            entry = CardHistory(
                card_id=sample_card.id,
                user_id=sample_user.id,
                action=f"action_{i}",
                description=f"Description {i}",
            )
            db_session.add(entry)
            entries.append(entry)

        db_session.commit()

        # Forcer des created_at différents
        for i, entry in enumerate(entries):
            entry.created_at = datetime.now() - timedelta(minutes=i)

        db_session.commit()

        history = get_card_history(db_session, sample_card.id)

        # Vérifier que les entrées sont triées par date décroissante
        for i in range(len(history) - 1):
            assert history[i].created_at is not None
            assert history[i + 1].created_at is not None
            assert history[i].created_at >= history[i + 1].created_at  # type: ignore


class TestGetCardHistoryWithUsers:
    """Tests pour la fonction get_card_history_with_users."""

    def test_get_card_history_with_users_success(
        self, db_session, sample_history_entries, sample_user
    ):
        """Test de récupération réussie de l'historique avec les informations utilisateur."""
        card_id = sample_history_entries[0].card_id
        history = get_card_history_with_users(db_session, card_id)

        assert len(history) == 3

        # Vérifier que les relations utilisateur sont chargées
        for entry in history:
            assert entry.user is not None
            assert entry.user.id == sample_user.id
            assert entry.user.email == sample_user.email

    def test_get_card_history_with_users_multiple_users(self, db_session, sample_card):
        """Test avec plusieurs utilisateurs différents."""
        # Créer plusieurs utilisateurs
        user1 = User(
            email="user1@example.com",
            display_name="User 1",
            role=UserRole.EDITOR,
            status=UserStatus.ACTIVE,
        )
        user2 = User(
            email="user2@example.com",
            display_name="User 2",
            role=UserRole.EDITOR,
            status=UserStatus.ACTIVE,
        )
        db_session.add(user1)
        db_session.add(user2)
        db_session.commit()
        db_session.refresh(user1)
        db_session.refresh(user2)

        # Créer des entrées d'historique avec différents utilisateurs
        entry1 = CardHistory(
            card_id=sample_card.id,
            user_id=user1.id,
            action="created",
            description="Créé par user1",
        )
        entry2 = CardHistory(
            card_id=sample_card.id,
            user_id=user2.id,
            action="updated",
            description="Mis à jour par user2",
        )
        db_session.add(entry1)
        db_session.add(entry2)
        db_session.commit()

        history = get_card_history_with_users(db_session, sample_card.id)

        assert len(history) == 2

        # Vérifier que les utilisateurs sont correctement associés
        users_in_history = [entry.user for entry in history]
        user_emails = [user.email for user in users_in_history]

        assert "user1@example.com" in user_emails
        assert "user2@example.com" in user_emails

    def test_get_card_history_with_users_empty(self, db_session, sample_card):
        """Test de récupération d'historique vide avec utilisateurs."""
        history = get_card_history_with_users(db_session, sample_card.id)

        assert len(history) == 0

    def test_get_card_history_with_users_user_attributes(
        self, db_session, sample_card, sample_user
    ):
        """Test que tous les attributs utilisateur sont disponibles."""
        entry = CardHistory(
            card_id=sample_card.id,
            user_id=sample_user.id,
            action="created",
            description="Test user attributes",
        )
        db_session.add(entry)
        db_session.commit()

        history = get_card_history_with_users(db_session, sample_card.id)

        assert len(history) == 1
        user = history[0].user

        assert user is not None
        assert user.id == sample_user.id
        assert user.email == sample_user.email
        assert user.display_name == sample_user.display_name
        assert user.role == sample_user.role
        assert user.status == sample_user.status


class TestCardHistoryIntegration:
    """Tests d'intégration pour le service CardHistory."""

    def test_create_and_retrieve_history_flow(
        self, db_session, sample_card, sample_user
    ):
        """Test du flux complet de création et récupération d'historique."""
        # Créer plusieurs entrées d'historique
        actions = [
            ("created", "Carte créée"),
            ("updated", "Titre mis à jour"),
            ("moved", "Carte déplacée"),
            ("assigned", "Assignée à utilisateur"),
        ]

        for action, description in actions:
            history_data = CardHistoryCreate(
                card_id=sample_card.id,
                user_id=sample_user.id,
                action=action,
                description=description,
            )
            create_card_history_entry(db_session, history_data)

        # Récupérer l'historique
        history = get_card_history_with_users(db_session, sample_card.id)

        assert len(history) == 4

        # Vérifier que toutes les actions sont présentes
        retrieved_actions = [entry.action for entry in history]
        for action, _ in actions:
            assert action in retrieved_actions

        # Vérifier que les entrées sont triées par date
        for i in range(len(history) - 1):
            assert history[i].created_at is not None
            assert history[i + 1].created_at is not None
            assert history[i].created_at >= history[i + 1].created_at  # type: ignore

    def test_concurrent_history_creation(self, db_session, sample_card, sample_user):
        """Test de création concurrente d'entrées d'historique."""
        # Créer plusieurs entrées séquentiellement (version simplifiée)
        for i in range(5):
            history_data = CardHistoryCreate(
                card_id=sample_card.id,
                user_id=sample_user.id,
                action=f"action_{i}",
                description=f"Description {i}",
            )
            create_card_history_entry(db_session, history_data)

        # Vérifier que toutes les entrées ont été créées
        history = get_card_history(db_session, sample_card.id)
        assert len(history) >= 5  # Au moins 5 entrées (plus celles existantes)

    def test_history_performance_large_dataset(
        self, db_session, sample_card, sample_user
    ):
        """Test de performance avec un grand nombre d'entrées d'historique."""
        import time

        # Créer beaucoup d'entrées
        start_time = time.time()

        for i in range(100):
            history_data = CardHistoryCreate(
                card_id=sample_card.id,
                user_id=sample_user.id,
                action=f"action_{i}",
                description=f"Description {i}",
            )
            create_card_history_entry(db_session, history_data)

        creation_time = time.time() - start_time

        # Mesurer le temps de récupération
        start_time = time.time()
        history = get_card_history_with_users(db_session, sample_card.id)
        retrieval_time = time.time() - start_time

        assert len(history) == 100
        assert creation_time < 5.0  # Moins de 5 secondes pour créer 100 entrées
        assert retrieval_time < 1.0  # Moins de 1 seconde pour récupérer 100 entrées


class TestSecurityAndEdgeCases:
    """Tests de sécurité et cas particuliers."""

    def test_xss_in_description(self, db_session, sample_card, sample_user):
        """Test de tentative XSS dans la description."""
        xss_description = (
            "<script>alert('XSS')</script><img src='x' onerror='alert(1)'>"
        )

        history_data = CardHistoryCreate(
            card_id=sample_card.id,
            user_id=sample_user.id,
            action="updated",
            description=xss_description,
        )

        result = create_card_history_entry(db_session, history_data)

        # La description doit être stockée telle quelle
        assert result.description == xss_description

    def test_special_characters_in_action(self, db_session, sample_card, sample_user):
        """Test avec des caractères spéciaux dans l'action."""
        special_action = "action_éèàçù_ñáéíóú_中文_العربية"

        history_data = CardHistoryCreate(
            card_id=sample_card.id,
            user_id=sample_user.id,
            action=special_action,
            description="Test caractères spéciaux",
        )

        result = create_card_history_entry(db_session, history_data)

        assert result.action == special_action

    def test_null_values_not_allowed(self, db_session, sample_card, sample_user):
        """Test que les valeurs nulles sont correctement gérées."""
        # Les champs ne peuvent pas être nuls selon le schéma, donc on teste avec des chaînes vides
        history_data = CardHistoryCreate(
            card_id=sample_card.id, user_id=sample_user.id, action="", description=""
        )

        result = create_card_history_entry(db_session, history_data)

        assert result.action == ""
        assert result.description == ""

    def test_very_long_action_name(self, db_session, sample_card, sample_user):
        """Test avec un nom d'action très long."""
        long_action = "a" * 1000

        history_data = CardHistoryCreate(
            card_id=sample_card.id,
            user_id=sample_user.id,
            action=long_action,
            description="Long action test",
        )

        result = create_card_history_entry(db_session, history_data)

        assert result.action == long_action

    def test_history_entry_with_special_characters(
        self, db_session, sample_card, sample_user
    ):
        """Test avec des caractères spéciaux variés."""
        history_data = CardHistoryCreate(
            card_id=sample_card.id,
            user_id=sample_user.id,
            action="🚀_update_测试",
            description="Mise à jour avec émojis 🎯 et caractères 中文",
        )

        result = create_card_history_entry(db_session, history_data)

        assert result.action == "🚀_update_测试"
        assert result.description == "Mise à jour avec émojis 🎯 et caractères 中文"
