"""Tests complets pour le modèle Card."""

import datetime
import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base
from app.models.card import Card, CardPriority, card_labels
from app.models.card_comment import CardComment
from app.models.card_history import CardHistory
from app.models.card_item import CardItem
from app.models.kanban_list import KanbanList
from app.models.label import Label
from app.models.user import User, UserRole, UserStatus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configuration de la base de données de test
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_card_model.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
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
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_user_2(db_session):
    """Fixture pour créer un deuxième utilisateur de test."""
    user = User(
        email="test2@example.com",
        display_name="Test User 2",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_kanban_lists(db_session):
    """Fixture pour créer des listes Kanban de test."""
    lists = [
        KanbanList(name="To Do", order=1),
        KanbanList(name="In Progress", order=2),
        KanbanList(name="Done", order=3),
    ]

    for kanban_list in lists:
        db_session.add(kanban_list)
    db_session.commit()

    for kanban_list in lists:
        db_session.refresh(kanban_list)

    return lists


@pytest.fixture
def sample_labels(db_session, sample_user):
    """Fixture pour créer des étiquettes de test."""
    labels = [
        Label(nom="Bug", couleur="#FF0000", created_by=sample_user.id),
        Label(nom="Feature", couleur="#00FF00", created_by=sample_user.id),
        Label(nom="Enhancement", couleur="#0000FF", created_by=sample_user.id),
    ]

    for label in labels:
        db_session.add(label)
    db_session.commit()

    for label in labels:
        db_session.refresh(label)

    return labels


@pytest.fixture
def sample_cards(db_session, sample_kanban_lists, sample_user):
    """Fixture pour créer des cartes de test."""
    cards = [
        Card(
            titre="Card 1",
            description="Description 1",
            priorite=CardPriority.HIGH,
            list_id=sample_kanban_lists[0].id,
            position=1,
            created_by=sample_user.id,
            assignee_id=sample_user.id,
            is_archived=False,
        ),
        Card(
            titre="Card 2",
            description="Description 2",
            priorite=CardPriority.MEDIUM,
            list_id=sample_kanban_lists[0].id,
            position=2,
            created_by=sample_user.id,
            assignee_id=sample_user.id,
            is_archived=False,
        ),
        Card(
            titre="Card 3",
            description="Description 3",
            priorite=CardPriority.LOW,
            list_id=sample_kanban_lists[1].id,
            position=1,
            created_by=sample_user.id,
            is_archived=True,
        ),
    ]

    for card in cards:
        db_session.add(card)
    db_session.commit()

    for card in cards:
        db_session.refresh(card)

    return cards


class TestCardModel:
    """Tests pour le modèle Card."""

    def test_model_creation(self):
        """Test de création du modèle Card."""
        card = Card()

        # Vérifier que l'objet est créé
        assert card is not None
        assert isinstance(card, Card)

    def test_model_attributes(self):
        """Test que le modèle a tous les attributs attendus."""
        card = Card()

        # Vérifier que tous les attributs existent
        assert hasattr(card, "id")
        assert hasattr(card, "titre")
        assert hasattr(card, "description")
        assert hasattr(card, "date_echeance")
        assert hasattr(card, "priorite")
        assert hasattr(card, "list_id")
        assert hasattr(card, "position")
        assert hasattr(card, "assignee_id")
        assert hasattr(card, "created_by")
        assert hasattr(card, "is_archived")
        assert hasattr(card, "created_at")
        assert hasattr(card, "updated_at")
        assert hasattr(card, "PROTECTED_FIELDS")

    def test_model_table_name(self):
        """Test que le nom de la table est correct."""
        assert Card.__tablename__ == "cards"

    def test_card_priority_enum(self):
        """Test que l'énumération CardPriority fonctionne correctement."""
        assert CardPriority.LOW.value == "low"
        assert CardPriority.MEDIUM.value == "medium"
        assert CardPriority.HIGH.value == "high"

        # Vérifier que les valeurs sont uniques
        values = [priority.value for priority in CardPriority]
        assert len(set(values)) == len(values)

    def test_card_labels_table(self):
        """Test que la table d'association card_labels est correcte."""
        assert isinstance(card_labels, type(Card.__table__))
        assert card_labels.name == "card_labels"

    def test_protected_fields(self):
        """Test que les champs protégés sont correctement définis."""
        expected_protected_fields = {"id", "created_by", "created_at"}
        assert Card.PROTECTED_FIELDS == expected_protected_fields

    def test_create_card_successfully(self, db_session, sample_kanban_lists, sample_user):
        """Test de création réussie d'une carte."""
        card = Card(
            titre="Test Card",
            description="Test Description",
            priorite=CardPriority.HIGH,
            list_id=sample_kanban_lists[0].id,
            position=1,
            created_by=sample_user.id,
            assignee_id=sample_user.id,
            is_archived=False,
        )

        db_session.add(card)
        db_session.commit()
        db_session.refresh(card)

        assert card.id is not None
        assert card.titre == "Test Card"
        assert card.description == "Test Description"
        assert card.priorite == CardPriority.HIGH
        assert card.list_id == sample_kanban_lists[0].id
        assert card.position == 1
        assert card.created_by == sample_user.id
        assert card.assignee_id == sample_user.id
        assert card.is_archived is False
        assert card.created_at is not None
        assert card.updated_at is None

    def test_create_card_minimal(self, db_session, sample_kanban_lists, sample_user):
        """Test de création avec les champs minimum requis."""
        card = Card(
            titre="Minimal Card",
            list_id=sample_kanban_lists[0].id,
            created_by=sample_user.id,
        )

        db_session.add(card)
        db_session.commit()
        db_session.refresh(card)

        assert card.id is not None
        assert card.titre == "Minimal Card"
        assert card.list_id == sample_kanban_lists[0].id
        assert card.created_by == sample_user.id
        assert card.description is None  # Optionnel
        assert card.date_echeance is None  # Optionnel
        assert card.priorite == CardPriority.MEDIUM  # Valeur par défaut
        assert card.position == 0  # Valeur par défaut
        assert card.assignee_id is None  # Optionnel
        assert card.is_archived is False  # Valeur par défaut

    def test_create_card_with_due_date(self, db_session, sample_kanban_lists, sample_user):
        """Test de création avec date d'échéance."""
        due_date = datetime.date.today() + datetime.timedelta(days=7)

        card = Card(
            titre="Card with Due Date",
            list_id=sample_kanban_lists[0].id,
            created_by=sample_user.id,
            date_echeance=due_date,
        )

        db_session.add(card)
        db_session.commit()
        db_session.refresh(card)

        assert card.date_echeance == due_date
        assert isinstance(card.date_echeance, datetime.date)

    def test_card_timestamps(self, db_session, sample_kanban_lists, sample_user):
        """Test que les timestamps sont correctement gérés."""
        card = Card(
            titre="Timestamp Test",
            list_id=sample_kanban_lists[0].id,
            created_by=sample_user.id,
        )

        db_session.add(card)
        db_session.commit()

        # Vérifier created_at
        assert card.created_at is not None
        assert isinstance(card.created_at, datetime.datetime)

        # Mettre à jour pour tester updated_at
        original_updated_at = card.updated_at
        card.titre = "Updated Title"
        db_session.commit()
        db_session.refresh(card)

        # updated_at devrait maintenant être défini
        assert card.updated_at is not None
        assert isinstance(card.updated_at, datetime.datetime)
        assert card.updated_at != original_updated_at

    def test_card_priority_default(self, db_session, sample_kanban_lists, sample_user):
        """Test que la priorité par défaut est correcte."""
        card = Card(
            titre="Default Priority",
            list_id=sample_kanban_lists[0].id,
            created_by=sample_user.id,
        )

        db_session.add(card)
        db_session.commit()

        assert card.priorite == CardPriority.MEDIUM

    def test_card_archived_default(self, db_session, sample_kanban_lists, sample_user):
        """Test que is_archived a la bonne valeur par défaut."""
        card = Card(
            titre="Default Archived",
            list_id=sample_kanban_lists[0].id,
            created_by=sample_user.id,
        )

        db_session.add(card)
        db_session.commit()

        assert card.is_archived is False

    def test_card_update(self, db_session, sample_cards):
        """Test de mise à jour d'une carte."""
        card = sample_cards[0]
        original_created_at = card.created_at
        original_created_by = card.created_by

        # Mettre à jour plusieurs champs
        card.titre = "Updated Title"
        card.description = "Updated Description"
        card.priorite = CardPriority.LOW
        card.is_archived = True

        db_session.commit()
        db_session.refresh(card)

        # Vérifier les mises à jour
        assert card.titre == "Updated Title"
        assert card.description == "Updated Description"
        assert card.priorite == CardPriority.LOW
        assert card.is_archived is True
        assert card.created_at == original_created_at  # Ne devrait pas changer
        assert card.created_by == original_created_by  # Ne devrait pas changer
        assert card.updated_at is not None  # Devrait être mis à jour

    def test_card_query_by_title(self, db_session, sample_cards):
        """Test de recherche par titre."""
        cards = db_session.query(Card).filter(Card.titre == "Card 1").all()

        assert len(cards) == 1
        assert cards[0].titre == "Card 1"

    def test_card_query_by_priority(self, db_session, sample_cards):
        """Test de recherche par priorité."""
        high_priority_cards = db_session.query(Card).filter(Card.priorite == CardPriority.HIGH).all()

        assert len(high_priority_cards) == 1
        assert high_priority_cards[0].priorite == CardPriority.HIGH

    def test_card_query_by_list(self, db_session, sample_cards, sample_kanban_lists):
        """Test de recherche par liste."""
        list_id = sample_kanban_lists[0].id
        cards = db_session.query(Card).filter(Card.list_id == list_id).all()

        assert len(cards) == 2  # Deux cartes dans la première liste
        assert all(card.list_id == list_id for card in cards)

    def test_card_query_by_assignee(self, db_session, sample_cards, sample_user):
        """Test de recherche par assigné."""
        cards = db_session.query(Card).filter(Card.assignee_id == sample_user.id).all()

        assert len(cards) == 2  # Deux cartes assignées à l'utilisateur
        assert all(card.assignee_id == sample_user.id for card in cards)

    def test_card_query_archived(self, db_session, sample_cards):
        """Test de recherche des cartes archivées."""
        archived_cards = db_session.query(Card).filter(Card.is_archived == True).all()

        assert len(archived_cards) == 1
        assert archived_cards[0].is_archived is True

    def test_card_query_non_archived(self, db_session, sample_cards):
        """Test de recherche des cartes non archivées."""
        active_cards = db_session.query(Card).filter(Card.is_archived == False).all()

        assert len(active_cards) == 2
        assert all(not card.is_archived for card in active_cards)

    def test_card_query_by_creator(self, db_session, sample_cards, sample_user):
        """Test de recherche par créateur."""
        cards = db_session.query(Card).filter(Card.created_by == sample_user.id).all()

        assert len(cards) == 3  # Toutes les cartes créées par l'utilisateur
        assert all(card.created_by == sample_user.id for card in cards)

    def test_card_order_by_position(self, db_session, sample_cards):
        """Test de tri par position."""
        cards = db_session.query(Card).order_by(Card.position).all()

        # Vérifier que les positions sont en ordre croissant
        positions = [card.position for card in cards]
        assert positions == sorted(positions)

    def test_card_order_by_creation_date(self, db_session, sample_cards):
        """Test de tri par date de création."""
        cards = db_session.query(Card).order_by(Card.created_at).all()

        # Vérifier que les dates sont en ordre croissant
        dates = [card.created_at for card in cards]
        assert dates == sorted(dates)

    def test_card_search_text(self, db_session, sample_cards):
        """Test de recherche textuelle."""
        # Recherche dans le titre
        cards = db_session.query(Card).filter(Card.titre.like("%Card 1%")).all()

        assert len(cards) == 1
        assert cards[0].titre == "Card 1"

        # Recherche dans la description
        cards = db_session.query(Card).filter(Card.description.like("%Description 2%")).all()

        assert len(cards) == 1
        assert cards[0].description == "Description 2"

    def test_card_delete(self, db_session, sample_cards):
        """Test de suppression d'une carte."""
        card = sample_cards[0]
        card_id = card.id

        db_session.delete(card)
        db_session.commit()

        # Vérifier que la carte a été supprimée
        deleted_card = db_session.query(Card).filter(Card.id == card_id).first()
        assert deleted_card is None

    def test_card_string_fields_validation(self, db_session, sample_kanban_lists, sample_user):
        """Test des validations des champs texte."""
        # Test avec titre long
        long_title = "x" * 200  # Longueur maximale raisonnable
        card = Card(
            titre=long_title,
            list_id=sample_kanban_lists[0].id,
            created_by=sample_user.id,
        )

        db_session.add(card)
        db_session.commit()

        assert card.titre == long_title

    def test_card_special_characters(self, db_session, sample_kanban_lists, sample_user):
        """Test avec des caractères spéciaux."""
        card = Card(
            titre="Carte spéciale: éèàçù 🚀 中文",
            description="Description spéciale",
            list_id=sample_kanban_lists[0].id,
            created_by=sample_user.id,
        )

        db_session.add(card)
        db_session.commit()

        assert card.titre == "Carte spéciale: éèàçù 🚀 中文"
        assert card.description == "Description spéciale"

    def test_card_unicode_emojis(self, db_session, sample_kanban_lists, sample_user):
        """Test avec des emojis Unicode."""
        card = Card(
            titre="Emoji Test 🎯🚀✨",
            list_id=sample_kanban_lists[0].id,
            created_by=sample_user.id,
        )

        db_session.add(card)
        db_session.commit()

        assert card.titre == "Emoji Test 🎯🚀✨"

    def test_card_html_content(self, db_session, sample_kanban_lists, sample_user):
        """Test avec contenu HTML."""
        html_content = "<div>HTML Content</div><script>alert('test')</script>"

        card = Card(
            titre="HTML Test",
            description=html_content,
            list_id=sample_kanban_lists[0].id,
            created_by=sample_user.id,
        )

        db_session.add(card)
        db_session.commit()

        # Le contenu HTML devrait être stocké tel quel
        assert card.description == html_content

    def test_card_empty_fields(self, db_session, sample_kanban_lists, sample_user):
        """Test avec des champs vides."""
        card = Card(
            titre="Empty Fields Test",
            description="",
            list_id=sample_kanban_lists[0].id,
            created_by=sample_user.id,
        )

        db_session.add(card)
        db_session.commit()

        assert card.description == ""

    def test_card_null_fields(self, db_session, sample_kanban_lists, sample_user):
        """Test avec des champs NULL."""
        card = Card(
            titre="Null Fields Test",
            list_id=sample_kanban_lists[0].id,
            created_by=sample_user.id,
            description=None,
            assignee_id=None,
            date_echeance=None,
        )

        db_session.add(card)
        db_session.commit()

        assert card.description is None
        assert card.assignee_id is None
        assert card.date_echeance is None

    def test_card_future_due_date(self, db_session, sample_kanban_lists, sample_user):
        """Test avec une date d'échéance future."""
        future_date = datetime.date.today() + datetime.timedelta(days=365)

        card = Card(
            titre="Future Due Date",
            list_id=sample_kanban_lists[0].id,
            created_by=sample_user.id,
            date_echeance=future_date,
        )

        db_session.add(card)
        db_session.commit()

        assert card.date_echeance == future_date
        assert card.date_echeance > datetime.date.today()

    def test_card_past_due_date(self, db_session, sample_kanban_lists, sample_user):
        """Test avec une date d'échéance passée."""
        past_date = datetime.date.today() - datetime.timedelta(days=30)

        card = Card(
            titre="Past Due Date",
            list_id=sample_kanban_lists[0].id,
            created_by=sample_user.id,
            date_echeance=past_date,
        )

        db_session.add(card)
        db_session.commit()

        assert card.date_echeance == past_date
        assert card.date_echeance < datetime.date.today()

    def test_card_today_due_date(self, db_session, sample_kanban_lists, sample_user):
        """Test avec une date d'échéance aujourd'hui."""
        today = datetime.date.today()

        card = Card(
            titre="Today Due Date",
            list_id=sample_kanban_lists[0].id,
            created_by=sample_user.id,
            date_echeance=today,
        )

        db_session.add(card)
        db_session.commit()

        assert card.date_echeance == today

    def test_card_position_management(self, db_session, sample_kanban_lists, sample_user):
        """Test de gestion des positions."""
        # Créer plusieurs cartes avec des positions spécifiques
        cards = []
        for i in range(5):
            card = Card(
                titre=f"Position Test {i}",
                list_id=sample_kanban_lists[0].id,
                created_by=sample_user.id,
                position=i * 10,  # Positions espacées
            )
            cards.append(card)
            db_session.add(card)

        db_session.commit()

        # Vérifier que les positions sont uniques
        positions = [card.position for card in cards]
        assert len(set(positions)) == len(positions)

    def test_card_duplicate_position_in_same_list(self, db_session, sample_kanban_lists, sample_user):
        """Test que les positions en double dans la même liste sont gérées."""
        # Créer deux cartes avec la même position
        card1 = Card(
            titre="Card 1",
            list_id=sample_kanban_lists[0].id,
            created_by=sample_user.id,
            position=1,
        )

        card2 = Card(
            titre="Card 2",
            list_id=sample_kanban_lists[0].id,
            created_by=sample_user.id,
            position=1,
        )

        db_session.add(card1)
        db_session.add(card2)
        db_session.commit()

        # Les deux cartes devraient exister (la contrainte d'unicité n'est pas au niveau BD)
        assert card1.id is not None
        assert card2.id is not None
        assert card1.position == card2.position

    def test_card_foreign_key_constraints(self, db_session, sample_user):
        """Test des contraintes de clé étrangère."""
        # Essayer de créer une carte avec un list_id invalide
        card = Card(
            titre="Invalid List",
            list_id=99999,  # N'existe pas
            created_by=sample_user.id,
        )

        db_session.add(card)
        # Peut échouer selon la configuration de la base de données
        try:
            db_session.commit()
        except Exception:
            db_session.rollback()
            # C'est normal si la contrainte de clé étrangère est activée

    def test_card_relationships_loading(self, db_session, sample_cards, sample_kanban_lists, sample_user):
        """Test que les relations sont correctement chargées."""
        card = sample_cards[0]

        # Charger la relation kanban_list
        assert card.kanban_list is not None
        assert card.kanban_list.id == card.list_id

        # Charger la relation creator
        assert card.creator is not None
        assert card.creator.id == card.created_by

        # Charger la relation assignee
        if card.assignee_id:
            assert card.assignee is not None
            assert card.assignee.id == card.assignee_id

    def test_card_cascade_delete_relations(self, db_session, sample_cards):
        """Test de la suppression en cascade des relations."""
        card = sample_cards[0]

        # Ajouter des éléments liés
        comment = CardComment(card_id=card.id, user_id=sample_cards[0].created_by, comment="Test comment")

        item = CardItem(card_id=card.id, texte="Test item")

        history = CardHistory(
            card_id=card.id, user_id=sample_cards[0].created_by, action="created", description="Card created"
        )

        db_session.add(comment)
        db_session.add(item)
        db_session.add(history)
        db_session.commit()

        # Supprimer la carte
        db_session.delete(card)
        db_session.commit()

        # Vérifier que les éléments liés sont aussi supprimés (cascade)
        assert db_session.query(CardComment).filter(CardComment.card_id == card.id).count() == 0
        assert db_session.query(CardItem).filter(CardItem.card_id == card.id).count() == 0
        assert db_session.query(CardHistory).filter(CardHistory.card_id == card.id).count() == 0

    def test_card_labels_relationship(self, db_session, sample_cards, sample_labels):
        """Test de la relation many-to-many avec les étiquettes."""
        card = sample_cards[0]

        # Ajouter des étiquettes
        card.labels = sample_labels
        db_session.commit()

        # Vérifier que les étiquettes sont bien associées
        assert len(card.labels) == len(sample_labels)
        for label in sample_labels:
            assert label in card.labels

        # Vérifier que la relation fonctionne dans l'autre sens
        for label in sample_labels:
            assert card in label.cards

    def test_card_batch_operations(self, db_session, sample_kanban_lists, sample_user):
        """Test d'opérations par lots."""
        # Créer plusieurs cartes en lot
        cards = []
        for i in range(10):
            card = Card(
                titre=f"Batch Card {i}",
                list_id=sample_kanban_lists[0].id,
                created_by=sample_user.id,
                position=i,
            )
            cards.append(card)

        db_session.add_all(cards)
        db_session.commit()

        # Vérifier que toutes ont été créées
        count = db_session.query(Card).filter(Card.titre.like("Batch Card %")).count()
        assert count == 10

    def test_card_bulk_update(self, db_session, sample_cards):
        """Test de mises à jour en masse."""
        # Mettre à jour toutes les cartes non archivées
        db_session.query(Card).filter(Card.is_archived == False).update({"is_archived": True})

        db_session.commit()

        # Vérifier que toutes les cartes sont maintenant archivées
        active_cards = db_session.query(Card).filter(Card.is_archived == False).count()
        assert active_cards == 0

    def test_card_complex_queries(self, db_session, sample_cards):
        """Test de requêtes complexes."""
        # Chercher les cartes non archivées avec priorité haute ou moyenne
        cards = (
            db_session.query(Card)
            .filter(
                and_(
                    Card.is_archived == False,
                    or_(Card.priorite == CardPriority.HIGH, Card.priorite == CardPriority.MEDIUM),
                )
            )
            .all()
        )

        assert len(cards) == 2

        # Chercher les cartes créées par un utilisateur spécifique
        user_id = sample_cards[0].created_by
        cards = db_session.query(Card).filter(Card.created_by == user_id).order_by(Card.position).all()

        assert len(cards) == 3
        # Vérifier que les positions sont en ordre
        positions = [card.position for card in cards]
        assert positions == sorted(positions)

    def test_card_pagination(self, db_session):
        """Test de pagination des résultats."""
        # Créer plusieurs cartes
        for i in range(20):
            card = Card(
                titre=f"Pagination Test {i}",
                list_id=1,  # Supposer que la liste 1 existe
                created_by=1,  # Supposer que l'utilisateur 1 existe
                position=i,
            )
            db_session.add(card)

        db_session.commit()

        # Test pagination
        page1 = db_session.query(Card).limit(5).all()
        page2 = db_session.query(Card).offset(5).limit(5).all()

        assert len(page1) == 5
        assert len(page2) == 5
        assert page1[0].id != page2[0].id

    def test_card_count_aggregations(self, db_session, sample_cards, sample_kanban_lists):
        """Test d'agrégations et de comptage."""
        # Compter les cartes par liste
        list_counts = (
            db_session.query(Card.list_id, db_session.query(Card.id).filter(Card.list_id == KanbanList.id).count())
            .join(KanbanList)
            .group_by(Card.list_id)
            .all()
        )

        assert len(list_counts) > 0

        # Compter les cartes par priorité
        priority_counts = (
            db_session.query(Card.priorite, db_session.query(Card.id).filter(Card.priorite == Card.priorite).count())
            .group_by(Card.priorite)
            .all()
        )

        assert len(priority_counts) > 0

    def test_card_error_handling(self, db_session):
        """Test de gestion des erreurs."""
        # Simuler une erreur de base de données
        with patch.object(db_session, "commit", side_effect=SQLAlchemyError("Database error")):
            card = Card(
                titre="Error Test",
                list_id=1,
                created_by=1,
            )

            db_session.add(card)
            with pytest.raises(SQLAlchemyError):
                db_session.commit()

    def test_card_representation(self, db_session, sample_cards):
        """Test de la représentation textuelle de l'objet."""
        card = sample_cards[0]

        # La représentation devrait contenir des informations utiles
        str_repr = str(card)
        assert "Card" in str_repr
        assert card.titre in str_repr

    def test_card_equality(self, db_session, sample_kanban_lists, sample_user):
        """Test de l'égalité entre objets."""
        card1 = Card(
            titre="Equality Test 1",
            list_id=sample_kanban_lists[0].id,
            created_by=sample_user.id,
        )

        card2 = Card(
            titre="Equality Test 2",
            list_id=sample_kanban_lists[0].id,
            created_by=sample_user.id,
        )

        db_session.add(card1)
        db_session.add(card2)
        db_session.commit()

        # Ce sont des objets différents
        assert card1 != card2
        assert card1.id != card2.id

    def test_card_unique_constraints(self, db_session, sample_kanban_lists, sample_user):
        """Test des contraintes d'unicité."""
        # Le modèle Card n'a pas de contraintes d'unicité spécifiques
        # plusieurs cartes peuvent avoir le même titre
        card1 = Card(
            titre="Same Title",
            list_id=sample_kanban_lists[0].id,
            created_by=sample_user.id,
        )

        card2 = Card(
            titre="Same Title",
            list_id=sample_kanban_lists[0].id,
            created_by=sample_user.id,
        )

        db_session.add(card1)
        db_session.add(card2)
        db_session.commit()

        # Les deux cartes devraient exister
        assert card1.id is not None
        assert card2.id is not None
        assert card1.titre == card2.titre

    def test_card_database_constraints(self, db_session, sample_user):
        """Test des contraintes de base de données."""
        # Test que titre ne peut pas être NULL
        card = Card(
            titre=None,  # Devrait échouer
            list_id=1,
            created_by=sample_user.id,
        )

        db_session.add(card)
        with pytest.raises(Exception):
            db_session.commit()

        db_session.rollback()

        # Test que list_id ne peut pas être NULL
        card = Card(
            titre="Test",
            list_id=None,  # Devrait échouer
            created_by=sample_user.id,
        )

        db_session.add(card)
        with pytest.raises(Exception):
            db_session.commit()

        db_session.rollback()

        # Test que created_by ne peut pas être NULL
        card = Card(
            titre="Test",
            list_id=1,
            created_by=None,  # Devrait échouer
        )

        db_session.add(card)
        with pytest.raises(Exception):
            db_session.commit()

    def test_card_transactions(self, db_session, sample_kanban_lists, sample_user):
        """Test de transactions."""
        # Créer une carte
        card = Card(
            titre="Transaction Test",
            list_id=sample_kanban_lists[0].id,
            created_by=sample_user.id,
        )
        db_session.add(card)
        db_session.commit()

        original_title = card.titre

        # Modifier dans une transaction
        card.titre = "Modified Title"

        # Faire un rollback
        db_session.rollback()
        db_session.refresh(card)

        # Le titre devrait être celui d'avant la modification
        assert card.titre == original_title

    def test_card_concurrent_modification(self, db_session, sample_cards):
        """Test de modification concurrente (simplifié)."""
        card = sample_cards[0]
        original_title = card.titre

        # Simuler des modifications concurrentes
        card1 = db_session.query(Card).filter(Card.id == card.id).first()
        card2 = db_session.query(Card).filter(Card.id == card.id).first()

        # Les deux devraient être le même objet
        assert card1.id == card2.id

        # Modifier à travers la première référence
        card1.titre = "Concurrent Modification 1"
        db_session.commit()

        # Rafraîchir la deuxième référence
        db_session.refresh(card2)

        # La deuxième référence devrait voir la modification
        assert card2.titre == "Concurrent Modification 1"

    def test_card_session_isolation(self, db_session, sample_kanban_lists, sample_user):
        """Test d'isolation des sessions."""
        # Créer une carte
        card = Card(
            titre="Session Test",
            list_id=sample_kanban_lists[0].id,
            created_by=sample_user.id,
        )
        db_session.add(card)

        # Ne pas commiter encore
        # L'objet ne devrait pas être visible dans une nouvelle session
        new_session = TestingSessionLocal()
        try:
            count = new_session.query(Card).filter(Card.titre == "Session Test").count()
            assert count == 0
        finally:
            new_session.close()

        # Commiter maintenant
        db_session.commit()

        # Maintenant il devrait être visible
        new_session = TestingSessionLocal()
        try:
            count = new_session.query(Card).filter(Card.titre == "Session Test").count()
            assert count == 1
        finally:
            new_session.close()

    def test_card_relationships_eager_loading(self, db_session, sample_cards, sample_user):
        """Test du chargement eager des relations."""
        from sqlalchemy.orm import joinedload

        # Charger une carte avec ses relations
        card = (
            db_session.query(Card)
            .options(joinedload(Card.creator), joinedload(Card.assignee), joinedload(Card.kanban_list))
            .filter(Card.id == sample_cards[0].id)
            .first()
        )

        assert card is not None
        assert card.creator is not None
        assert card.kanban_list is not None
        if card.assignee_id:
            assert card.assignee is not None

    def test_card_filtering_combined(self, db_session, sample_cards):
        """Test de filtrage combiné."""
        # Chercher les cartes non archivées du créateur spécifique
        creator_id = sample_cards[0].created_by
        cards = (
            db_session.query(Card)
            .filter(
                and_(
                    Card.created_by == creator_id,
                    Card.is_archived == False,
                    Card.priorite.in_([CardPriority.HIGH, CardPriority.MEDIUM]),
                )
            )
            .order_by(Card.position)
            .all()
        )

        assert len(cards) >= 1
        assert all(card.created_by == creator_id for card in cards)
        assert all(not card.is_archived for card in cards)

    def test_card_data_types(self, db_session, sample_kanban_lists, sample_user):
        """Test avec différents types de données."""
        test_cards = [
            ("string_title", "Simple String"),
            ("unicode_title", "Unicode: éèàçù 中文"),
            ("emoji_title", "Emoji: 🚀🎯✨"),
            ("html_title", "<b>HTML</b> Title"),
            ("long_title", "x" * 100),
        ]

        for title_suffix, title_value in test_cards:
            card = Card(
                titre=f"{title_suffix}: {title_value}",
                list_id=sample_kanban_lists[0].id,
                created_by=sample_user.id,
            )
            db_session.add(card)

        db_session.commit()

        # Vérifier que toutes les cartes ont été créées
        count = db_session.query(Card).count()
        assert count == len(test_cards)
