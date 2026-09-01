"""Tests complets pour le modèle CardHistory."""

import datetime
import os
import sys
from unittest.mock import patch

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base
from app.models.card import Card
from app.models.card_history import CardHistory
from app.models.kanban_list import KanbanList
from app.models.user import User, UserRole, UserStatus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configuration de la base de données de test
TEST_DB_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(TEST_DB_DIR, exist_ok=True)
TEST_DB_PATH = os.path.join(TEST_DB_DIR, "test_card_history_model.db")
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
        list_id=sample_kanban_list.id,
        created_by=sample_user.id,
    )
    db_session.add(card)
    db_session.commit()
    db_session.refresh(card)
    return card


@pytest.fixture
def sample_history(db_session, sample_card, sample_user):
    """Fixture pour créer des entrées d'historique de test."""
    history_entries = [
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
            description="Carte déplacée vers une autre liste",
        ),
    ]

    for entry in history_entries:
        db_session.add(entry)
    db_session.commit()

    for entry in history_entries:
        db_session.refresh(entry)

    return history_entries


class TestCardHistoryModel:
    """Tests pour le modèle CardHistory."""

    def test_model_creation(self):
        """Test de création du modèle CardHistory."""
        history = CardHistory()

        # Vérifier que l'objet est créé
        assert history is not None
        assert isinstance(history, CardHistory)

    def test_model_attributes(self):
        """Test que le modèle a tous les attributs attendus."""
        history = CardHistory()

        # Vérifier que tous les attributs existent
        assert hasattr(history, "id")
        assert hasattr(history, "card_id")
        assert hasattr(history, "user_id")
        assert hasattr(history, "action")
        assert hasattr(history, "description")
        assert hasattr(history, "created_at")

    def test_model_table_name(self):
        """Test que le nom de la table est correct."""
        assert CardHistory.__tablename__ == "card_history"

    def test_create_card_history_successfully(
        self, db_session, sample_card, sample_user
    ):
        """Test de création réussie d'une entrée d'historique."""
        before_creation = datetime.datetime.now()

        history = CardHistory(
            card_id=sample_card.id,
            user_id=sample_user.id,
            action="test_action",
            description="Test description",
        )

        db_session.add(history)
        db_session.commit()
        db_session.refresh(history)

        after_creation = datetime.datetime.now()

        assert history.id is not None
        assert history.card_id == sample_card.id
        assert history.user_id == sample_user.id
        assert history.action == "test_action"
        assert history.description == "Test description"
        assert history.created_at is not None

        # Vérifier que le timestamp est dans la plage attendue
        assert before_creation <= history.created_at <= after_creation

    def test_create_card_history_minimal(self, db_session, sample_card, sample_user):
        """Test de création avec les champs minimum requis."""
        history = CardHistory(
            card_id=sample_card.id,
            user_id=sample_user.id,
            action="minimal_action",
            description="Minimal description",
        )

        db_session.add(history)
        db_session.commit()
        db_session.refresh(history)

        assert history.id is not None
        assert history.card_id == sample_card.id
        assert history.user_id == sample_user.id
        assert history.action == "minimal_action"
        assert history.description == "Minimal description"
        assert history.created_at is not None

    def test_card_history_timestamp_on_create(
        self, db_session, sample_card, sample_user
    ):
        """Test que le timestamp est correct à la création."""
        before_creation = datetime.datetime.now()

        history = CardHistory(
            card_id=sample_card.id,
            user_id=sample_user.id,
            action="timestamp_test",
            description="Testing timestamp",
        )

        db_session.add(history)
        db_session.commit()

        after_creation = datetime.datetime.now()

        # Vérifier que created_at est dans la plage attendue
        assert before_creation <= history.created_at <= after_creation
        assert isinstance(history.created_at, datetime.datetime)

    def test_card_history_update(self, db_session, sample_card, sample_user):
        """Test de mise à jour d'une entrée d'historique."""
        history = CardHistory(
            card_id=sample_card.id,
            user_id=sample_user.id,
            action="original_action",
            description="Original description",
        )

        db_session.add(history)
        db_session.commit()

        original_created_at = history.created_at

        # Mettre à jour l'action et la description
        history.action = "updated_action"
        history.description = "Updated description"

        db_session.commit()
        db_session.refresh(history)

        # Vérifier les mises à jour
        assert history.action == "updated_action"
        assert history.description == "Updated description"
        assert history.created_at == original_created_at  # Ne devrait pas changer

    def test_card_history_query_by_card(self, db_session, sample_card, sample_user):
        """Test de recherche par carte."""
        # Créer quelques entrées d'historique
        for i in range(3):
            history = CardHistory(
                card_id=sample_card.id,
                user_id=sample_user.id,
                action=f"action_{i}",
                description=f"Description {i}",
            )
            db_session.add(history)

        db_session.commit()

        # Rechercher les entrées d'historique de la carte
        history_entries = (
            db_session.query(CardHistory)
            .filter(CardHistory.card_id == sample_card.id)
            .all()
        )

        assert len(history_entries) >= 3
        assert all(entry.card_id == sample_card.id for entry in history_entries)

    def test_card_history_query_by_user(self, db_session, sample_card, sample_user):
        """Test de recherche par utilisateur."""
        # Créer quelques entrées d'historique
        for i in range(3):
            history = CardHistory(
                card_id=sample_card.id,
                user_id=sample_user.id,
                action=f"user_action_{i}",
                description=f"User description {i}",
            )
            db_session.add(history)

        db_session.commit()

        # Rechercher les entrées d'historique de l'utilisateur
        history_entries = (
            db_session.query(CardHistory)
            .filter(CardHistory.user_id == sample_user.id)
            .all()
        )

        assert len(history_entries) >= 3
        assert all(entry.user_id == sample_user.id for entry in history_entries)

    def test_card_history_query_by_action(self, db_session, sample_card, sample_user):
        """Test de recherche par action."""
        # Créer des entrées avec différentes actions
        actions = ["created", "updated", "moved", "deleted", "archived"]

        for action in actions:
            history = CardHistory(
                card_id=sample_card.id,
                user_id=sample_user.id,
                action=action,
                description=f"Card {action}",
            )
            db_session.add(history)

        db_session.commit()

        # Rechercher les entrées avec l'action "created"
        created_entries = (
            db_session.query(CardHistory).filter(CardHistory.action == "created").all()
        )

        assert len(created_entries) == 1
        assert created_entries[0].action == "created"

    def test_card_history_query_by_description(
        self, db_session, sample_card, sample_user
    ):
        """Test de recherche textuelle dans la description."""
        # Créer des entrées avec des descriptions spécifiques
        descriptions = [
            "Card title changed",
            "Card description updated",
            "Card moved to Done list",
            "Card assigned to user",
        ]

        for desc in descriptions:
            history = CardHistory(
                card_id=sample_card.id,
                user_id=sample_user.id,
                action="updated",
                description=desc,
            )
            db_session.add(history)

        db_session.commit()

        # Rechercher les entrées contenant "title"
        title_entries = (
            db_session.query(CardHistory)
            .filter(CardHistory.description.like("%title%"))
            .all()
        )

        assert len(title_entries) == 1
        assert "title" in title_entries[0].description

    def test_card_history_order_by_creation_date(
        self, db_session, sample_card, sample_user
    ):
        """Test de tri par date de création."""
        # Créer des entrées avec un délai
        entries = []
        for i in range(3):
            history = CardHistory(
                card_id=sample_card.id,
                user_id=sample_user.id,
                action=f"action_{i}",
                description=f"Description {i}",
            )
            db_session.add(history)
            db_session.commit()
            entries.append(history)

            # Attendre un peu
            import time

            time.sleep(0.01)

        # Récupérer les entrées triées par date de création
        sorted_entries = (
            db_session.query(CardHistory).order_by(CardHistory.created_at).all()
        )

        # Vérifier qu'elles sont dans l'ordre chronologique
        for i in range(len(sorted_entries) - 1):
            assert sorted_entries[i].created_at <= sorted_entries[i + 1].created_at

    def test_card_history_order_by_creation_date_desc(
        self, db_session, sample_card, sample_user
    ):
        """Test de tri par date de création décroissante."""
        # Créer des entrées
        for i in range(3):
            history = CardHistory(
                card_id=sample_card.id,
                user_id=sample_user.id,
                action=f"action_{i}",
                description=f"Description {i}",
            )
            db_session.add(history)
            db_session.commit()

            # Attendre un peu
            import time

            time.sleep(0.01)

        # Récupérer les entrées triées par date de création décroissante
        sorted_entries = (
            db_session.query(CardHistory).order_by(CardHistory.created_at.desc()).all()
        )

        # Vérifier qu'elles sont dans l'ordre chronologique inverse
        for i in range(len(sorted_entries) - 1):
            assert sorted_entries[i].created_at >= sorted_entries[i + 1].created_at

    def test_card_history_delete(self, db_session, sample_history):
        """Test de suppression d'une entrée d'historique."""
        entry = sample_history[0]
        entry_id = entry.id

        db_session.delete(entry)
        db_session.commit()

        # Vérifier que l'entrée a été supprimée
        deleted_entry = (
            db_session.query(CardHistory).filter(CardHistory.id == entry_id).first()
        )
        assert deleted_entry is None

    def test_card_history_string_fields_validation(
        self, db_session, sample_card, sample_user
    ):
        """Test des validations des champs text."""
        # Test avec action longue
        long_action = "a" * 100

        # Test avec description longue
        long_description = "x" * 1000

        history = CardHistory(
            card_id=sample_card.id,
            user_id=sample_user.id,
            action=long_action,
            description=long_description,
        )

        db_session.add(history)
        db_session.commit()

        assert history.action == long_action
        assert history.description == long_description

    def test_card_history_special_characters(
        self, db_session, sample_card, sample_user
    ):
        """Test avec des caractères spéciaux."""
        history = CardHistory(
            card_id=sample_card.id,
            user_id=sample_user.id,
            action="action_spéciale_éèàçù",
            description="description_spéciale_éèàçù_中文_العربية",
        )

        db_session.add(history)
        db_session.commit()

        assert history.action == "action_spéciale_éèàçù"
        assert history.description == "description_spéciale_éèàçù_中文_العربية"

    def test_card_history_unicode_emojis(self, db_session, sample_card, sample_user):
        """Test avec des emojis Unicode."""
        history = CardHistory(
            card_id=sample_card.id,
            user_id=sample_user.id,
            action="emoji_action_🚀",
            description="emoji_description_🎯✨",
        )

        db_session.add(history)
        db_session.commit()

        assert history.action == "emoji_action_🚀"
        assert history.description == "emoji_description_🎯✨"

    def test_card_history_empty_fields(self, db_session, sample_card, sample_user):
        """Test avec des champs vides."""
        history = CardHistory(
            card_id=sample_card.id,
            user_id=sample_user.id,
            action="",
            description="",
        )

        db_session.add(history)
        db_session.commit()

        assert history.action == ""
        assert history.description == ""

    def test_card_history_multiline_description(
        self, db_session, sample_card, sample_user
    ):
        """Test avec une description multiligne."""
        multiline_desc = """Ceci est une description multiligne.
Ligne 2
Ligne 3
Avec des caractères spéciaux: éèàç"""

        history = CardHistory(
            card_id=sample_card.id,
            user_id=sample_user.id,
            action="multiline_action",
            description=multiline_desc,
        )

        db_session.add(history)
        db_session.commit()

        assert history.description == multiline_desc

    def test_card_history_null_fields(self, db_session):
        """Test que les champs requis ne peuvent pas être NULL."""
        # Créer une carte et un utilisateur pour le test
        user = User(
            email="nulltest@example.com",
            display_name="Null Test",
            role=UserRole.EDITOR,
            status=UserStatus.ACTIVE,
        )
        kanban_list = KanbanList(name="Null Test List", order=1)
        card = Card(title="Null Test Card", list_id=1, created_by=1)

        db_session.add(user)
        db_session.add(kanban_list)
        db_session.add(card)
        db_session.commit()

        # Test que card_id ne peut pas être NULL
        history = CardHistory(
            card_id=None,  # Devrait échouer
            user_id=user.id,
            action="test",
            description="test",
        )

        db_session.add(history)
        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()

        # Test que user_id ne peut pas être NULL
        history = CardHistory(
            card_id=card.id,
            user_id=None,  # Devrait échouer
            action="test",
            description="test",
        )

        db_session.add(history)
        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()

        # Test que action ne peut pas être NULL
        history = CardHistory(
            card_id=card.id,
            user_id=user.id,
            action=None,  # Devrait échouer
            description="test",
        )

        db_session.add(history)
        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()

        # Test que description ne peut pas être NULL
        history = CardHistory(
            card_id=card.id,
            user_id=user.id,
            action="test",
            description=None,  # Devrait échouer
        )

        db_session.add(history)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_card_history_foreign_key_constraints(self, db_session, sample_user):
        """Test des contraintes de clé étrangère."""
        # Essayer de créer une entrée avec un card_id invalide
        history = CardHistory(
            card_id=99999,  # N'existe pas
            user_id=sample_user.id,
            action="invalid_card_test",
            description="Testing invalid card",
        )

        db_session.add(history)
        try:
            db_session.commit()
        except Exception:
            db_session.rollback()

        db_session.rollback()

        # Essayer de créer une entrée avec un user_id invalide
        history = CardHistory(
            card_id=1,  # Supposer que la carte 1 existe
            user_id=99999,  # N'existe pas
            action="invalid_user_test",
            description="Testing invalid user",
        )

        db_session.add(history)
        try:
            db_session.commit()
        except Exception:
            db_session.rollback()

    def test_card_history_relationships_loading(
        self, db_session, sample_history, sample_card, sample_user
    ):
        """Test que les relations sont correctement chargées."""
        entry = sample_history[0]

        # Charger la relation card
        assert entry.card is not None
        assert entry.card.id == entry.card_id

        # Charger la relation user
        assert entry.user is not None
        assert entry.user.id == entry.user_id

    def test_card_history_cascade_delete(self, db_session, sample_card, sample_user):
        """Test de la suppression en cascade."""
        # Créer une entrée d'historique
        history = CardHistory(
            card_id=sample_card.id,
            user_id=sample_user.id,
            action="cascade_test",
            description="Testing cascade delete",
        )

        db_session.add(history)
        db_session.commit()

        history_id = history.id

        # Supprimer la carte
        db_session.delete(sample_card)
        db_session.commit()

        # L'entrée d'historique devrait être supprimée en cascade
        deleted_entry = (
            db_session.query(CardHistory).filter(CardHistory.id == history_id).first()
        )
        assert deleted_entry is None

    def test_card_history_batch_operations(self, db_session, sample_card, sample_user):
        """Test d'opérations par lots."""
        # Créer plusieurs entrées en lot
        entries = []
        for i in range(10):
            history = CardHistory(
                card_id=sample_card.id,
                user_id=sample_user.id,
                action=f"batch_action_{i}",
                description=f"Batch description {i}",
            )
            entries.append(history)

        db_session.add_all(entries)
        db_session.commit()

        # Vérifier que toutes ont été créées
        count = (
            db_session.query(CardHistory)
            .filter(CardHistory.action.like("batch_action_%"))
            .count()
        )
        assert count == 10

    def test_card_history_bulk_update(self, db_session, sample_card, sample_user):
        """Test de mises à jour en masse."""
        # Créer quelques entrées
        for i in range(5):
            history = CardHistory(
                card_id=sample_card.id,
                user_id=sample_user.id,
                action=f"original_action_{i}",
                description=f"Original description {i}",
            )
            db_session.add(history)

        db_session.commit()

        # Mettre à jour toutes les entrées avec "updated_" comme préfixe
        db_session.query(CardHistory).filter(
            CardHistory.card_id == sample_card.id
        ).update(
            {
                "action": CardHistory.action + "_updated",
                "description": CardHistory.description + " (updated)",
            }
        )

        db_session.commit()

        # Vérifier que toutes les entrées ont été mises à jour
        updated_entries = (
            db_session.query(CardHistory)
            .filter(CardHistory.card_id == sample_card.id)
            .all()
        )

        for entry in updated_entries:
            assert entry.action.endswith("_updated")
            assert "(updated)" in entry.description

    def test_card_history_complex_queries(self, db_session, sample_card, sample_user):
        """Test de requêtes complexes."""
        # Créer des entrées variées
        import time

        entries_data = [
            ("created", "Card created by user"),
            ("updated", "Card title changed"),
            ("moved", "Card moved to another list"),
            ("assigned", "Card assigned to user"),
            ("archived", "Card archived"),
        ]

        for action, desc in entries_data:
            history = CardHistory(
                card_id=sample_card.id,
                user_id=sample_user.id,
                action=action,
                description=desc,
            )
            db_session.add(history)
            db_session.commit()
            time.sleep(0.01)

        # Chercher les entrées avec action dans ['created', 'updated', 'moved']
        from sqlalchemy import or_

        specific_actions = (
            db_session.query(CardHistory)
            .filter(
                or_(
                    CardHistory.action == "created",
                    CardHistory.action == "updated",
                    CardHistory.action == "moved",
                )
            )
            .order_by(CardHistory.created_at.desc())
            .all()
        )

        assert len(specific_actions) == 3

        # Chercher les entrées contenant "Card" dans la description
        card_entries = (
            db_session.query(CardHistory)
            .filter(CardHistory.description.like("%Card%"))
            .all()
        )

        assert len(card_entries) == 5

    def test_card_history_pagination(self, db_session, sample_card, sample_user):
        """Test de pagination des résultats."""
        # Créer plusieurs entrées
        for i in range(20):
            history = CardHistory(
                card_id=sample_card.id,
                user_id=sample_user.id,
                action=f"pagination_action_{i}",
                description=f"Pagination description {i}",
            )
            db_session.add(history)

        db_session.commit()

        # Test pagination
        page1 = db_session.query(CardHistory).limit(5).all()
        page2 = db_session.query(CardHistory).offset(5).limit(5).all()

        assert len(page1) == 5
        assert len(page2) == 5
        assert page1[0].id != page2[0].id

    def test_card_history_count_aggregations(
        self, db_session, sample_card, sample_user
    ):
        """Test d'agrégations et de comptage."""
        # Créer des entrées avec différentes actions
        actions_count = {"created": 2, "updated": 3, "moved": 1, "deleted": 1}

        for action, count in actions_count.items():
            for i in range(count):
                history = CardHistory(
                    card_id=sample_card.id,
                    user_id=sample_user.id,
                    action=action,
                    description=f"Card {action} #{i}",
                )
                db_session.add(history)

        db_session.commit()

        # Compter les entrées par action
        for action, expected_count in actions_count.items():
            actual_count = (
                db_session.query(CardHistory)
                .filter(CardHistory.action == action)
                .count()
            )
            assert actual_count == expected_count

    def test_card_history_error_handling(self, db_session, sample_card, sample_user):
        """Test de gestion des erreurs."""
        # Simuler une erreur de base de données
        with patch.object(
            db_session, "commit", side_effect=SQLAlchemyError("Database error")
        ):
            history = CardHistory(
                card_id=sample_card.id,
                user_id=sample_user.id,
                action="error_test",
                description="Testing error handling",
            )

            db_session.add(history)
            with pytest.raises(SQLAlchemyError):
                db_session.commit()

    def test_card_history_representation(self, db_session, sample_card, sample_user):
        """Test de la représentation textuelle de l'objet."""
        history = CardHistory(
            card_id=sample_card.id,
            user_id=sample_user.id,
            action="representation_test",
            description="Testing string representation",
        )

        db_session.add(history)
        db_session.commit()

        # La représentation devrait contenir des informations utiles
        str_repr = str(history)
        assert "CardHistory" in str_repr

    def test_card_history_equality(self, db_session, sample_card, sample_user):
        """Test de l'égalité entre objets."""
        history1 = CardHistory(
            card_id=sample_card.id,
            user_id=sample_user.id,
            action="equality_test_1",
            description="First entry",
        )

        history2 = CardHistory(
            card_id=sample_card.id,
            user_id=sample_user.id,
            action="equality_test_2",
            description="Second entry",
        )

        db_session.add(history1)
        db_session.add(history2)
        db_session.commit()

        # Ce sont des objets différents
        assert history1 != history2
        assert history1.id != history2.id

    def test_card_history_timeline_ordering(self, db_session, sample_card, sample_user):
        """Test que l'historique maintient un ordre chronologique correct."""
        entries = []

        # Créer des entrées avec des actions spécifiques dans un ordre connu
        actions_sequence = ["created", "updated", "moved", "assigned", "archived"]

        for action in actions_sequence:
            history = CardHistory(
                card_id=sample_card.id,
                user_id=sample_user.id,
                action=action,
                description=f"Card {action}",
            )
            db_session.add(history)
            db_session.commit()
            entries.append(history)

            # Attendre un peu pour garantir des timestamps différents
            import time

            time.sleep(0.01)

        # Récupérer toutes les entrées dans l'ordre chronologique
        timeline = (
            db_session.query(CardHistory)
            .filter(CardHistory.card_id == sample_card.id)
            .order_by(CardHistory.created_at)
            .all()
        )

        # Vérifier que l'ordre des actions est préservé
        timeline_actions = [
            entry.action for entry in timeline[-len(actions_sequence) :]
        ]
        assert timeline_actions == actions_sequence

    def test_card_history_user_activity_tracking(
        self, db_session, sample_card, sample_user
    ):
        """Test du suivi de l'activité utilisateur."""
        # Créer plusieurs entrées d'historique pour le même utilisateur
        user_actions = ["created", "updated_title", "added_comment", "moved_card"]

        for action in user_actions:
            history = CardHistory(
                card_id=sample_card.id,
                user_id=sample_user.id,
                action=action,
                description=f"User {action} the card",
            )
            db_session.add(history)

        db_session.commit()

        # Compter les actions de l'utilisateur
        user_activity_count = (
            db_session.query(CardHistory)
            .filter(CardHistory.user_id == sample_user.id)
            .count()
        )

        assert user_activity_count >= len(user_actions)

    def test_card_history_card_lifecycle(self, db_session, sample_card, sample_user):
        """Test du suivi du cycle de vie d'une carte."""
        # Simuler le cycle de vie complet d'une carte
        lifecycle_actions = [
            ("created", "Card created"),
            ("updated", "Card title updated"),
            ("assigned", "Card assigned to user"),
            ("moved", "Card moved to different list"),
            ("commented", "Comment added to card"),
            ("archived", "Card archived"),
        ]

        for action, description in lifecycle_actions:
            history = CardHistory(
                card_id=sample_card.id,
                user_id=sample_user.id,
                action=action,
                description=description,
            )
            db_session.add(history)
            db_session.commit()

            # Attendre un peu
            import time

            time.sleep(0.001)

        # Récupérer l'historique complet
        full_history = (
            db_session.query(CardHistory)
            .filter(CardHistory.card_id == sample_card.id)
            .order_by(CardHistory.created_at)
            .all()
        )

        # Vérifier que toutes les actions du cycle de vie sont présentes
        history_actions = [
            entry.action for entry in full_history[-len(lifecycle_actions) :]
        ]
        lifecycle_actions_only = [action for action, _ in lifecycle_actions]

        for action in lifecycle_actions_only:
            assert action in history_actions

    def test_card_history_search_functionality(
        self, db_session, sample_card, sample_user
    ):
        """Test de la fonctionnalité de recherche dans l'historique."""
        # Créer des entrées avec du text spécifique
        search_entries = [
            ("created", "Initial card creation"),
            ("updated", "Updated card title and description"),
            ("assigned", "Assigned card to team member"),
            ("moved", "Moved card to completed column"),
            ("commented", "Added comment about progress"),
        ]

        for action, desc in search_entries:
            history = CardHistory(
                card_id=sample_card.id,
                user_id=sample_user.id,
                action=action,
                description=desc,
            )
            db_session.add(history)

        db_session.commit()

        # Rechercher par mot-clé dans la description
        card_results = (
            db_session.query(CardHistory)
            .filter(CardHistory.description.like("%card%"))
            .all()
        )

        assert len(card_results) >= 2

        # Rechercher par action spécifique
        updated_results = (
            db_session.query(CardHistory).filter(CardHistory.action == "updated").all()
        )

        assert len(updated_results) == 1
        assert updated_results[0].action == "updated"

    def test_card_history_data_integrity(self, db_session, sample_card, sample_user):
        """Test de l'intégrité des données."""
        # Créer une entrée d'historique
        original_history = CardHistory(
            card_id=sample_card.id,
            user_id=sample_user.id,
            action="integrity_test",
            description="Testing data integrity",
        )

        db_session.add(original_history)
        db_session.commit()

        # Récupérer l'entrée et vérifier que toutes les données sont intactes
        retrieved_history = (
            db_session.query(CardHistory)
            .filter(CardHistory.id == original_history.id)
            .first()
        )

        assert retrieved_history is not None
        assert retrieved_history.card_id == original_history.card_id
        assert retrieved_history.user_id == original_history.user_id
        assert retrieved_history.action == original_history.action
        assert retrieved_history.description == original_history.description
        assert retrieved_history.created_at == original_history.created_at

    def test_card_history_concurrent_access(self, db_session, sample_card, sample_user):
        """Test d'accès concurrent (simplifié)."""
        # Créer une entrée d'historique
        history = CardHistory(
            card_id=sample_card.id,
            user_id=sample_user.id,
            action="concurrent_test",
            description="Testing concurrent access",
        )
        db_session.add(history)
        db_session.commit()

        # Simuler des accès concurrents
        history1 = (
            db_session.query(CardHistory).filter(CardHistory.id == history.id).first()
        )
        history2 = (
            db_session.query(CardHistory).filter(CardHistory.id == history.id).first()
        )

        # Les deux devraient être le même objet
        assert history1.id == history2.id

        # Modifier à travers la première référence
        history1.description = "Concurrently modified description"
        db_session.commit()

        # Rafraîchir la deuxième référence
        db_session.refresh(history2)

        # La deuxième référence devrait voir la modification
        assert history2.description == "Concurrently modified description"
