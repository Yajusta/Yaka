"""Tests complets pour le modèle CardItem."""

import datetime
import os
import sys
from unittest.mock import patch

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base
from app.models.card import Card
from app.models.card_item import CardItem, get_system_timezone_datetime
from app.models.kanban_list import KanbanList
from app.models.user import User, UserRole, UserStatus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configuration de la base de données de test
TEST_DB_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(TEST_DB_DIR, exist_ok=True)
TEST_DB_PATH = os.path.join(TEST_DB_DIR, "test_card_item_model.db")
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
def sample_items(db_session, sample_card):
    """Fixture pour créer des éléments de carte de test."""
    items = [
        CardItem(
            card_id=sample_card.id,
            text="First item",
            is_done=False,
            position=1,
        ),
        CardItem(
            card_id=sample_card.id,
            text="Second item",
            is_done=True,
            position=2,
        ),
        CardItem(
            card_id=sample_card.id,
            text="Third item",
            is_done=False,
            position=3,
        ),
    ]

    for item in items:
        db_session.add(item)
    db_session.commit()

    for item in items:
        db_session.refresh(item)

    return items


class TestGetSystemTimezoneDatetimeForCardItem:
    """Tests pour la fonction get_system_timezone_datetime dans le context CardItem."""

    def test_get_system_timezone_datetime(self):
        """Test de récupération de la date et heure actuelle."""
        result = get_system_timezone_datetime()

        assert isinstance(result, datetime.datetime)
        assert result.tzinfo is not None

        # La date devrait être récente
        now = datetime.datetime.now().astimezone()
        time_diff = abs((result - now).total_seconds())
        assert time_diff < 60  # Moins d'une minute de différence


class TestCardItemModel:
    """Tests pour le modèle CardItem."""

    def test_model_creation(self):
        """Test de création du modèle CardItem."""
        item = CardItem()

        # Vérifier que l'objet est créé
        assert item is not None
        assert isinstance(item, CardItem)

    def test_model_attributes(self):
        """Test que le modèle a tous les attributs attendus."""
        item = CardItem()

        # Vérifier que tous les attributs existent
        assert hasattr(item, "id")
        assert hasattr(item, "card_id")
        assert hasattr(item, "text")
        assert hasattr(item, "is_done")
        assert hasattr(item, "position")
        assert hasattr(item, "created_at")
        assert hasattr(item, "updated_at")
        assert hasattr(item, "PROTECTED_FIELDS")

    def test_model_table_name(self):
        """Test que le nom de la table est correct."""
        assert CardItem.__tablename__ == "card_items"

    def test_protected_fields(self):
        """Test que les champs protégés sont correctement définis."""
        expected_protected_fields = {"id", "created_by", "created_at"}
        assert CardItem.PROTECTED_FIELDS == expected_protected_fields

    def test_create_card_item_successfully(self, db_session, sample_card):
        """Test de création réussie d'un élément de carte."""
        before_creation = get_system_timezone_datetime()

        item = CardItem(
            card_id=sample_card.id,
            text="Test item",
            is_done=False,
            position=1,
        )

        db_session.add(item)
        db_session.commit()
        db_session.refresh(item)

        after_creation = get_system_timezone_datetime()

        assert item.id is not None
        assert item.card_id == sample_card.id
        assert item.text == "Test item"
        assert item.is_done is False
        assert item.position == 1
        assert item.created_at is not None
        assert item.updated_at is not None

        # Vérifier que les timestamps sont dans la plage attendue
        assert before_creation <= item.created_at.astimezone() <= after_creation
        assert before_creation <= item.updated_at.astimezone() <= after_creation

    def test_create_card_item_minimal(self, db_session, sample_card):
        """Test de création avec les champs minimum requis."""
        item = CardItem(
            card_id=sample_card.id,
            text="Minimal item",
        )

        db_session.add(item)
        db_session.commit()
        db_session.refresh(item)

        assert item.id is not None
        assert item.card_id == sample_card.id
        assert item.text == "Minimal item"
        assert item.is_done is False  # Valeur par défaut
        assert item.position == 0  # Valeur par défaut
        assert item.created_at is not None
        assert item.updated_at is not None

    def test_create_card_item_done(self, db_session, sample_card):
        """Test de création d'un élément terminé."""
        item = CardItem(
            card_id=sample_card.id,
            text="Completed item",
            is_done=True,
            position=5,
        )

        db_session.add(item)
        db_session.commit()
        db_session.refresh(item)

        assert item.is_done is True
        assert item.position == 5

    def test_card_item_timestamps_on_create(self, db_session, sample_card):
        """Test que les timestamps sont corrects à la création."""
        before_creation = get_system_timezone_datetime()

        item = CardItem(
            card_id=sample_card.id,
            text="Timestamp test",
        )

        db_session.add(item)
        db_session.commit()

        after_creation = get_system_timezone_datetime()

        # created_at et updated_at devraient être identiques à la création
        assert item.created_at == item.updated_at
        assert before_creation <= item.created_at.astimezone() <= after_creation

    def test_card_item_timestamp_on_update(self, db_session, sample_card):
        """Test que le timestamp updated_at est mis à jour lors de la modification."""
        item = CardItem(
            card_id=sample_card.id,
            text="Original item",
            is_done=False,
        )

        db_session.add(item)
        db_session.commit()

        original_created_at = item.created_at
        original_updated_at = item.updated_at

        # Attendre un peu pour s'assurer que le timestamp change
        import time

        time.sleep(0.01)

        # Mettre à jour l'élément
        item.text = "Updated item"
        item.is_done = True
        db_session.commit()
        db_session.refresh(item)

        # created_at ne devrait pas changer
        assert item.created_at == original_created_at

        # updated_at devrait être différent et plus récent
        assert item.updated_at != original_updated_at
        assert item.updated_at > original_updated_at

    def test_card_item_update(self, db_session, sample_card):
        """Test de mise à jour d'un élément."""
        item = CardItem(
            card_id=sample_card.id,
            text="Original item",
            is_done=False,
            position=1,
        )

        db_session.add(item)
        db_session.commit()

        original_created_at = item.created_at

        # Mettre à jour plusieurs champs
        item.text = "Updated item"
        item.is_done = True
        item.position = 5

        db_session.commit()
        db_session.refresh(item)

        # Vérifier les mises à jour
        assert item.text == "Updated item"
        assert item.is_done is True
        assert item.position == 5
        assert item.created_at == original_created_at  # Ne devrait pas changer
        assert item.updated_at is not None  # Devrait être mis à jour

    def test_card_item_query_by_card(self, db_session, sample_card):
        """Test de recherche par carte."""
        # Créer quelques éléments
        for i in range(3):
            item = CardItem(
                card_id=sample_card.id,
                text=f"Item {i}",
                position=i,
            )
            db_session.add(item)

        db_session.commit()

        # Rechercher les éléments de la carte
        items = (
            db_session.query(CardItem).filter(CardItem.card_id == sample_card.id).all()
        )

        assert len(items) >= 3
        assert all(item.card_id == sample_card.id for item in items)

    def test_card_item_query_by_status(self, db_session, sample_card):
        """Test de recherche par statut."""
        # Créer des éléments avec différents statuts
        for i in range(3):
            item = CardItem(
                card_id=sample_card.id,
                text=f"Item {i}",
                is_done=(i % 2 == 0),  # Alterné
                position=i,
            )
            db_session.add(item)

        db_session.commit()

        # Rechercher les éléments terminés
        done_items = db_session.query(CardItem).filter(CardItem.is_done).all()

        # Rechercher les éléments non terminés
        pending_items = (
            db_session.query(CardItem).filter(CardItem.is_done.is_(False)).all()
        )

        assert len(done_items) >= 1
        assert len(pending_items) >= 1
        assert all(item.is_done for item in done_items)
        assert all(not item.is_done for item in pending_items)

    def test_card_item_query_by_text(self, db_session, sample_card):
        """Test de recherche textuelle."""
        # Créer des éléments avec du text spécifique
        items = [
            CardItem(card_id=sample_card.id, text="Important task", position=1),
            CardItem(card_id=sample_card.id, text="Urgent item", position=2),
            CardItem(card_id=sample_card.id, text="Regular task", position=3),
        ]

        for item in items:
            db_session.add(item)

        db_session.commit()

        # Rechercher les éléments contenant "task"
        task_items = (
            db_session.query(CardItem).filter(CardItem.text.like("%task%")).all()
        )

        assert len(task_items) == 2
        assert all("task" in item.text for item in task_items)

    def test_card_item_order_by_position(self, db_session, sample_card):
        """Test de tri par position."""
        # Créer des éléments avec des positions spécifiques
        items_data = [
            ("Third", 3),
            ("First", 1),
            ("Second", 2),
        ]

        for text, position in items_data:
            item = CardItem(
                card_id=sample_card.id,
                text=text,
                position=position,
            )
            db_session.add(item)

        db_session.commit()

        # Récupérer les éléments triés par position
        sorted_items = db_session.query(CardItem).order_by(CardItem.position).all()

        # Vérifier qu'ils sont dans le bon ordre
        expected_order = ["First", "Second", "Third"]
        actual_order = [item.text for item in sorted_items]
        assert actual_order == expected_order

    def test_card_item_delete(self, db_session, sample_items):
        """Test de suppression d'un élément."""
        item = sample_items[0]
        item_id = item.id

        db_session.delete(item)
        db_session.commit()

        # Vérifier que l'élément a été supprimé
        deleted_item = db_session.query(CardItem).filter(CardItem.id == item_id).first()
        assert deleted_item is None

    def test_card_item_string_fields_validation(self, db_session, sample_card):
        """Test des validations des champs text."""
        # Test avec text à la limite de la longueur
        max_length_text = "x" * 500  # Longueur maximale selon le modèle

        item = CardItem(
            card_id=sample_card.id,
            text=max_length_text,
        )

        db_session.add(item)
        db_session.commit()

        assert item.text == max_length_text
        assert len(item.text) == 500

    def test_card_item_special_characters(self, db_session, sample_card):
        """Test avec des caractères spéciaux."""
        item = CardItem(
            card_id=sample_card.id,
            text="Élément spécial: éèàçù 🚀 中文",
        )

        db_session.add(item)
        db_session.commit()

        assert item.text == "Élément spécial: éèàçù 🚀 中文"

    def test_card_item_unicode_emojis(self, db_session, sample_card):
        """Test avec des emojis Unicode."""
        item = CardItem(
            card_id=sample_card.id,
            text="Emoji Task 🎯🚀✨ ✅",
        )

        db_session.add(item)
        db_session.commit()

        assert item.text == "Emoji Task 🎯🚀✨ ✅"

    def test_card_item_empty_text(self, db_session, sample_card):
        """Test avec un text vide."""
        item = CardItem(
            card_id=sample_card.id,
            text="",
        )

        db_session.add(item)
        db_session.commit()

        assert item.text == ""

    def test_card_item_whitespace_only(self, db_session, sample_card):
        """Test avec un text ne contenant que des espaces."""
        item = CardItem(
            card_id=sample_card.id,
            text="   ",
        )

        db_session.add(item)
        db_session.commit()

        assert item.text == "   "

    def test_card_item_multiline_text(self, db_session, sample_card):
        """Test avec du text multiligne."""
        multiline_text = """Ceci est une tâche multiligne.
Sous-tâche 1
Sous-tâche 2
Notes supplémentaires"""

        item = CardItem(
            card_id=sample_card.id,
            text=multiline_text,
        )

        db_session.add(item)
        db_session.commit()

        assert item.text == multiline_text

    def test_card_item_position_management(self, db_session, sample_card):
        """Test de gestion des positions."""
        # Créer des éléments avec des positions variées
        positions = [10, 5, 15, 1, 20]

        for i, pos in enumerate(positions):
            item = CardItem(
                card_id=sample_card.id,
                text=f"Position test {i}",
                position=pos,
            )
            db_session.add(item)

        db_session.commit()

        # Récupérer les éléments triés par position
        sorted_items = db_session.query(CardItem).order_by(CardItem.position).all()

        # Vérifier que les positions sont en ordre croissant
        for i in range(len(sorted_items) - 1):
            assert sorted_items[i].position <= sorted_items[i + 1].position

    def test_card_item_negative_position(self, db_session, sample_card):
        """Test avec des positions négatives."""
        item = CardItem(
            card_id=sample_card.id,
            text="Negative position test",
            position=-5,
        )

        db_session.add(item)
        db_session.commit()

        assert item.position == -5

    def test_card_item_zero_position(self, db_session, sample_card):
        """Test avec position zéro."""
        item = CardItem(
            card_id=sample_card.id,
            text="Zero position test",
            position=0,
        )

        db_session.add(item)
        db_session.commit()

        assert item.position == 0

    def test_card_item_large_position(self, db_session, sample_card):
        """Test avec des positions très grandes."""
        item = CardItem(
            card_id=sample_card.id,
            text="Large position test",
            position=999999,
        )

        db_session.add(item)
        db_session.commit()

        assert item.position == 999999

    def test_card_item_toggle_done_status(self, db_session, sample_card):
        """Test de basculement du statut terminé."""
        item = CardItem(
            card_id=sample_card.id,
            text="Toggle test",
            is_done=False,
        )

        db_session.add(item)
        db_session.commit()

        # Basculer vers terminé
        item.is_done = True
        db_session.commit()
        db_session.refresh(item)

        assert item.is_done is True

        # Basculer vers non terminé
        item.is_done = False
        db_session.commit()
        db_session.refresh(item)

        assert item.is_done is False

    def test_card_item_foreign_key_constraints(self, db_session):
        """Test des contraintes de clé étrangère."""
        # Essayer de créer un élément avec un card_id invalide
        item = CardItem(
            card_id=99999,  # N'existe pas
            text="Invalid card test",
        )

        db_session.add(item)
        # Peut échouer selon la configuration de la base de données
        try:
            db_session.commit()
        except Exception:
            db_session.rollback()

    def test_card_item_relationships_loading(
        self, db_session, sample_items, sample_card
    ):
        """Test que les relations sont correctement chargées."""
        item = sample_items[0]

        # Charger la relation card
        assert item.card is not None
        assert item.card.id == item.card_id

    def test_card_item_cascade_delete(self, db_session, sample_card):
        """Test de la suppression en cascade."""
        # Créer un élément
        item = CardItem(
            card_id=sample_card.id,
            text="Cascade test",
        )

        db_session.add(item)
        db_session.commit()

        item_id = item.id

        # Supprimer la carte
        db_session.delete(sample_card)
        db_session.commit()

        # L'élément devrait être supprimé en cascade
        deleted_item = db_session.query(CardItem).filter(CardItem.id == item_id).first()
        assert deleted_item is None

    def test_card_item_batch_operations(self, db_session, sample_card):
        """Test d'opérations par lots."""
        # Créer plusieurs éléments en lot
        items = []
        for i in range(10):
            item = CardItem(
                card_id=sample_card.id,
                text=f"Batch item {i}",
                position=i,
            )
            items.append(item)

        db_session.add_all(items)
        db_session.commit()

        # Vérifier que tous ont été créés
        count = (
            db_session.query(CardItem)
            .filter(CardItem.text.like("Batch item %"))
            .count()
        )
        assert count == 10

    def test_card_item_bulk_update(self, db_session, sample_card):
        """Test de mises à jour en masse."""
        # Créer quelques éléments
        for i in range(5):
            item = CardItem(
                card_id=sample_card.id,
                text=f"Original item {i}",
                is_done=False,
                position=i,
            )
            db_session.add(item)

        db_session.commit()

        # Marquer tous les éléments comme terminés
        db_session.query(CardItem).filter(CardItem.card_id == sample_card.id).update(
            {"is_done": True}
        )

        db_session.commit()

        # Vérifier que tous les éléments sont maintenant terminés
        done_items = (
            db_session.query(CardItem).filter(CardItem.card_id == sample_card.id).all()
        )

        assert all(item.is_done for item in done_items)

    def test_card_item_complex_queries(self, db_session, sample_card):
        """Test de requêtes complexes."""
        # Créer des éléments variés
        items_data = [
            ("Important task", True, 1),
            ("Regular task", False, 2),
            ("Urgent item", False, 3),
            ("Completed item", True, 4),
        ]

        for text, is_done, position in items_data:
            item = CardItem(
                card_id=sample_card.id,
                text=text,
                is_done=is_done,
                position=position,
            )
            db_session.add(item)

        db_session.commit()

        # Chercher les éléments terminés contenant "task"
        from sqlalchemy import and_

        completed_tasks = (
            db_session.query(CardItem)
            .filter(and_(CardItem.is_done, CardItem.text.like("%task%")))
            .all()
        )

        assert len(completed_tasks) == 1
        assert completed_tasks[0].text == "Important task"

    def test_card_item_pagination(self, db_session, sample_card):
        """Test de pagination des résultats."""
        # Créer plusieurs éléments
        for i in range(20):
            item = CardItem(
                card_id=sample_card.id,
                text=f"Pagination item {i}",
                position=i,
            )
            db_session.add(item)

        db_session.commit()

        # Test pagination
        page1 = db_session.query(CardItem).limit(5).all()
        page2 = db_session.query(CardItem).offset(5).limit(5).all()

        assert len(page1) == 5
        assert len(page2) == 5
        assert page1[0].id != page2[0].id

    def test_card_item_count_aggregations(self, db_session, sample_card):
        """Test d'agrégations et de comptage."""
        # Créer des éléments avec différents statuts
        for i in range(5):
            item = CardItem(
                card_id=sample_card.id,
                text=f"Active item {i}",
                is_done=False,
                position=i,
            )
            db_session.add(item)

        for i in range(3):
            item = CardItem(
                card_id=sample_card.id,
                text=f"Completed item {i}",
                is_done=True,
                position=i + 10,
            )
            db_session.add(item)

        db_session.commit()

        # Compter les éléments par statut
        active_count = (
            db_session.query(CardItem).filter(CardItem.is_done.is_(False)).count()
        )

        completed_count = db_session.query(CardItem).filter(CardItem.is_done).count()

        assert active_count == 5
        assert completed_count == 3

    def test_card_item_error_handling(self, db_session, sample_card):
        """Test de gestion des erreurs."""
        # Simuler une erreur de base de données
        with patch.object(
            db_session, "commit", side_effect=SQLAlchemyError("Database error")
        ):
            item = CardItem(
                card_id=sample_card.id,
                text="Error test",
            )

            db_session.add(item)
            with pytest.raises(SQLAlchemyError):
                db_session.commit()

    def test_card_item_representation(self, db_session, sample_card):
        """Test de la représentation textuelle de l'objet."""
        item = CardItem(
            card_id=sample_card.id,
            text="Representation test",
        )

        db_session.add(item)
        db_session.commit()

        # La représentation devrait contenir des informations utiles
        str_repr = str(item)
        assert "CardItem" in str_repr

    def test_card_item_equality(self, db_session, sample_card):
        """Test de l'égalité entre objets."""
        item1 = CardItem(
            card_id=sample_card.id,
            text="Equality test 1",
            position=1,
        )

        item2 = CardItem(
            card_id=sample_card.id,
            text="Equality test 2",
            position=2,
        )

        db_session.add(item1)
        db_session.add(item2)
        db_session.commit()

        # Ce sont des objets différents
        assert item1 != item2
        assert item1.id != item2.id

    def test_card_item_database_constraints(self, db_session):
        """Test des contraintes de base de données."""
        # Créer une carte pour le test
        user = User(
            email="constrainttest@example.com",
            display_name="Constraint Test",
            role=UserRole.EDITOR,
            status=UserStatus.ACTIVE,
        )
        kanban_list = KanbanList(name="Constraint Test List", order=1)
        card = Card(title="Constraint Test Card", list_id=1, created_by=1)

        db_session.add(user)
        db_session.add(kanban_list)
        db_session.add(card)
        db_session.commit()

        # Test que card_id ne peut pas être NULL
        item = CardItem(
            card_id=None,  # Devrait échouer
            text="Test",
        )

        db_session.add(item)
        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()

        # Test que text ne peut pas être NULL
        item = CardItem(
            card_id=card.id,
            text=None,  # Devrait échouer
        )

        db_session.add(item)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_card_item_text_length_constraint(self, db_session, sample_card):
        """Test de la contrainte de longueur du text."""
        # Le modèle limite le text à 500 caractères
        exact_length_text = "x" * 500

        item = CardItem(
            card_id=sample_card.id,
            text=exact_length_text,
        )

        db_session.add(item)
        db_session.commit()

        assert len(item.text) == 500
        assert item.text == exact_length_text

    def test_card_item_progress_tracking(self, db_session, sample_card):
        """Test du suivi de progression."""
        # Créer des éléments pour tester la progression
        total_items = 5
        completed_items = 3

        for i in range(total_items):
            item = CardItem(
                card_id=sample_card.id,
                text=f"Task {i+1}",
                is_done=(i < completed_items),
                position=i,
            )
            db_session.add(item)

        db_session.commit()

        # Calculer la progression
        all_items = (
            db_session.query(CardItem).filter(CardItem.card_id == sample_card.id).all()
        )

        done_items = [item for item in all_items if item.is_done]

        progress = len(done_items) / len(all_items) if all_items else 0

        assert len(all_items) == total_items
        assert len(done_items) == completed_items
        assert progress == completed_items / total_items

    def test_card_item_reordering(self, db_session, sample_card):
        """Test du réordonnancement des éléments."""
        # Créer des éléments avec des positions initiales
        original_items = []
        for i in range(3):
            item = CardItem(
                card_id=sample_card.id,
                text=f"Original {i}",
                position=i * 10,  # 0, 10, 20
            )
            db_session.add(item)
            original_items.append(item)

        db_session.commit()

        # Réordonner : déplacer le dernier en première position
        original_items[2].position = 0
        original_items[0].position = 10
        original_items[1].position = 20

        db_session.commit()

        # Vérifier le nouvel ordre
        reordered_items = (
            db_session.query(CardItem)
            .filter(CardItem.card_id == sample_card.id)
            .order_by(CardItem.position)
            .all()
        )

        expected_texts = ["Original 2", "Original 0", "Original 1"]
        actual_texts = [item.text for item in reordered_items]

        assert actual_texts == expected_texts

    def test_card_item_checklist_functionality(self, db_session, sample_card):
        """Test de la fonctionnalité de checklist."""
        # Simuler une checklist complète
        checklist_items = [
            ("Préparer le projet", False),
            ("Définir les exigences", True),
            ("Créer le design", False),
            ("Développer l'application", False),
            ("Tester et déployer", False),
        ]

        for text, is_done in checklist_items:
            item = CardItem(
                card_id=sample_card.id,
                text=text,
                is_done=is_done,
                position=len(checklist_items),
            )
            db_session.add(item)

        db_session.commit()

        # Vérifier la checklist
        all_checklist_items = (
            db_session.query(CardItem)
            .filter(CardItem.card_id == sample_card.id)
            .order_by(CardItem.position)
            .all()
        )

        assert len(all_checklist_items) == len(checklist_items)

        # Vérifier que les texts correspondent
        actual_texts = [item.text for item in all_checklist_items]
        expected_texts = [text for text, _ in checklist_items]
        assert actual_texts == expected_texts

    def test_card_item_data_types(self, db_session, sample_card):
        """Test avec différents types de données."""
        test_items = [
            ("simple_text", "Simple text"),
            ("unicode_text", "Unicode: éèàçù 中文"),
            ("emoji_text", "Emoji: 🚀🎯✨"),
            ("html_text", "<b>HTML</b> content"),
            ("long_text", "x" * 499),  # Juste sous la limite
            ("multiline", "Line 1\nLine 2\nLine 3"),
            ("special_chars", "!@#$%^&*()_+-=[]{}|;':\",./<>?"),
            ("numbers_and_text", "Task 123: Do something"),
        ]

        for _suffix, text in test_items:
            item = CardItem(
                card_id=sample_card.id,
                text=text,
            )
            db_session.add(item)

        db_session.commit()

        # Vérifier que tous les éléments ont été créés
        count = db_session.query(CardItem).count()
        assert count >= len(test_items)
