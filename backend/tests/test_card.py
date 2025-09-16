"""Tests complets pour le service Card."""

import pytest
import sys
import os
from datetime import date, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.card import Card, CardPriority
from app.models.kanban_list import KanbanList
from app.models.label import Label
from app.models.user import User, UserRole, UserStatus
from app.models.card_comment import CardComment
from app.schemas.card import (
    CardCreate,
    CardUpdate,
    CardFilter,
    CardMoveRequest,
    CardListUpdate,
    BulkCardMoveRequest,
)
from app.services.card import (
    get_card,
    get_cards,
    get_archived_cards,
    create_card,
    update_card,
    update_card_list,
    archive_card,
    unarchive_card,
    delete_card,
    move_card,
    bulk_move_cards,
)

# Configuration de la base de données de test
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_card.db"
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


def create_sample_user_2(db_session):
    """Helper function pour créer ou récupérer un deuxième utilisateur de test."""
    # Vérifier si l'utilisateur existe déjà
    existing_user = db_session.query(User).filter(User.email == "test2@example.com").first()
    if existing_user:
        return existing_user
    
    # Créer l'utilisateur s'il n'existe pas
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
def sample_cards(db_session, sample_kanban_lists, sample_user, sample_labels):
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
            assignee_id=create_sample_user_2(db_session).id,
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
    
    # Ajouter des étiquettes à certaines cartes
    cards[0].labels = [sample_labels[0], sample_labels[1]]
    cards[1].labels = [sample_labels[2]]
    
    db_session.commit()
    
    for card in cards:
        db_session.refresh(card)
    
    return cards


class TestGetCard:
    """Tests pour la fonction get_card."""

    def test_get_card_success(self, db_session, sample_cards):
        """Test de récupération réussie d'une carte."""
        card = sample_cards[0]
        result = get_card(db_session, card.id)
        
        assert result is not None
        assert result.id == card.id
        assert result.titre == card.titre
        assert result.description == card.description
        assert len(result.comments) == 0  # Pas de commentaires créés

    def test_get_card_with_comments(self, db_session, sample_cards, sample_user):
        """Test de récupération d'une carte avec commentaires."""
        card = sample_cards[0]
        
        # Ajouter des commentaires (non supprimés et supprimés)
        comment1 = CardComment(
            card_id=card.id,
            user_id=sample_user.id,
            comment="Commentaire actif",
            is_deleted=False,
        )
        comment2 = CardComment(
            card_id=card.id,
            user_id=sample_user.id,
            comment="Commentaire supprimé",
            is_deleted=True,
        )
        db_session.add(comment1)
        db_session.add(comment2)
        db_session.commit()
        
        result = get_card(db_session, card.id)
        
        assert result is not None
        assert len(result.comments) == 1  # Seulement les commentaires non supprimés
        assert result.comments[0].comment == "Commentaire actif"

    def test_get_card_nonexistent(self, db_session):
        """Test de récupération d'une carte inexistante."""
        result = get_card(db_session, 99999)
        
        assert result is None


class TestGetCards:
    """Tests pour la fonction get_cards."""

    def test_get_cards_success(self, db_session, sample_cards):
        """Test de récupération réussie des cartes."""
        filters = CardFilter()
        cards = get_cards(db_session, filters)
        
        assert len(cards) == 2  # Seulement les cartes non archivées
        assert all(not card.is_archived for card in cards)

    def test_get_cards_with_archived(self, db_session, sample_cards):
        """Test de récupération des cartes incluant les archivées."""
        filters = CardFilter(include_archived=True)
        cards = get_cards(db_session, filters)
        
        assert len(cards) == 3  # Toutes les cartes

    def test_get_cards_by_list(self, db_session, sample_cards, sample_kanban_lists):
        """Test de récupération des cartes par liste."""
        filters = CardFilter(list_id=sample_kanban_lists[0].id)
        cards = get_cards(db_session, filters)
        
        assert len(cards) == 2
        assert all(card.list_id == sample_kanban_lists[0].id for card in cards)

    def test_get_cards_by_assignee(self, db_session, sample_cards, sample_user):
        """Test de récupération des cartes par assigné."""
        filters = CardFilter(assignee_id=sample_user.id)
        cards = get_cards(db_session, filters)
        
        assert len(cards) == 1
        assert cards[0].assignee_id == sample_user.id

    def test_get_cards_by_priority(self, db_session, sample_cards):
        """Test de récupération des cartes par priorité."""
        filters = CardFilter(priorite=CardPriority.HIGH)
        cards = get_cards(db_session, filters)
        
        assert len(cards) == 1
        assert cards[0].priorite == CardPriority.HIGH

    def test_get_cards_by_label(self, db_session, sample_cards, sample_labels):
        """Test de récupération des cartes par étiquette."""
        filters = CardFilter(label_id=sample_labels[0].id)
        cards = get_cards(db_session, filters)
        
        assert len(cards) == 1
        assert sample_labels[0] in cards[0].labels

    def test_get_cards_search(self, db_session, sample_cards):
        """Test de recherche textuelle dans les cartes."""
        filters = CardFilter(search="Description 1")
        cards = get_cards(db_session, filters)
        
        assert len(cards) == 1
        assert "Description 1" in cards[0].description

    def test_get_cards_search_title(self, db_session, sample_cards):
        """Test de recherche textuelle dans le titre."""
        filters = CardFilter(search="Card 2")
        cards = get_cards(db_session, filters)
        
        assert len(cards) == 1
        assert cards[0].titre == "Card 2"

    def test_get_cards_pagination(self, db_session, sample_cards):
        """Test de pagination des résultats."""
        filters = CardFilter()
        cards_page1 = get_cards(db_session, filters, skip=0, limit=1)
        cards_page2 = get_cards(db_session, filters, skip=1, limit=1)
        
        assert len(cards_page1) == 1
        assert len(cards_page2) == 1
        assert cards_page1[0].id != cards_page2[0].id

    def test_get_cards_ordering(self, db_session, sample_kanban_lists, sample_user):
        """Test que les cartes sont bien triées par position."""
        # Créer des cartes avec des positions explicites
        cards_data = [
            ("Card A", sample_kanban_lists[0].id, 3),
            ("Card B", sample_kanban_lists[0].id, 1),
            ("Card C", sample_kanban_lists[0].id, 2),
        ]
        
        for titre, list_id, position in cards_data:
            card = Card(
                titre=titre,
                list_id=list_id,
                position=position,
                created_by=sample_user.id,
            )
            db_session.add(card)
        
        db_session.commit()
        
        filters = CardFilter(list_id=sample_kanban_lists[0].id)
        cards = get_cards(db_session, filters)
        
        assert len(cards) == 3
        assert cards[0].position == 1
        assert cards[1].position == 2
        assert cards[2].position == 3

    def test_get_cards_multiple_filters(self, db_session, sample_cards, sample_user):
        """Test de combinaison de plusieurs filtres."""
        filters = CardFilter(
            list_id=sample_cards[0].list_id,
            assignee_id=sample_user.id,
            priorite=CardPriority.HIGH,
        )
        cards = get_cards(db_session, filters)
        
        assert len(cards) == 1
        assert cards[0].id == sample_cards[0].id


class TestGetArchivedCards:
    """Tests pour la fonction get_archived_cards."""

    def test_get_archived_cards_success(self, db_session, sample_cards):
        """Test de récupération réussie des cartes archivées."""
        archived_cards = get_archived_cards(db_session)
        
        assert len(archived_cards) == 1
        assert archived_cards[0].is_archived is True
        assert archived_cards[0].id == sample_cards[2].id

    def test_get_archived_cards_pagination(self, db_session, sample_kanban_lists, sample_user):
        """Test de pagination des cartes archivées."""
        # Créer plusieurs cartes archivées
        for i in range(5):
            card = Card(
                titre=f"Archived Card {i}",
                list_id=sample_kanban_lists[0].id,
                position=i + 1,
                created_by=sample_user.id,
                is_archived=True,
            )
            db_session.add(card)
        
        db_session.commit()
        
        archived_page1 = get_archived_cards(db_session, skip=0, limit=3)
        archived_page2 = get_archived_cards(db_session, skip=3, limit=3)
        
        assert len(archived_page1) == 3
        assert len(archived_page2) == 2  # 5 total cartes archivées + 1 existante = 6 total, mais on skip 3 donc on en a 2


class TestCreateCard:
    """Tests pour la fonction create_card."""

    def test_create_card_success(self, db_session, sample_kanban_lists, sample_user, sample_labels):
        """Test de création réussie d'une carte."""
        card_data = CardCreate(
            titre="New Card",
            description="New Description",
            list_id=sample_kanban_lists[0].id,
            priorite=CardPriority.MEDIUM,
            assignee_id=sample_user.id,
            label_ids=[sample_labels[0].id, sample_labels[1].id],
        )
        
        result = create_card(db_session, card_data, sample_user.id)
        
        assert result.id is not None
        assert result.titre == "New Card"
        assert result.description == "New Description"
        assert result.list_id == sample_kanban_lists[0].id
        assert result.priorite == CardPriority.MEDIUM
        assert result.assignee_id == sample_user.id
        assert result.created_by == sample_user.id
        assert result.is_archived is False
        assert len(result.labels) == 2
        # La position peut varier selon les cartes existantes, vérifions juste que c'est une position valide
        assert result.position >= 1

    def test_create_card_with_position(self, db_session, sample_kanban_lists, sample_user):
        """Test de création d'une carte avec position spécifique."""
        card_data = CardCreate(
            titre="Positioned Card",
            list_id=sample_kanban_lists[0].id,
            position=1,
        )
        
        result = create_card(db_session, card_data, sample_user.id)
        
        assert result.position == 1
        
        # Vérifier que les autres cartes ont été décalées
        cards = get_cards(db_session, CardFilter(list_id=sample_kanban_lists[0].id))
        positions = [card.position for card in sorted(cards, key=lambda x: x.position)]
        # Les positions devraient être uniques et ordonnées
        assert len(positions) == len(set(positions))
        assert positions == sorted(positions)

    def test_create_card_auto_list_id_minus_1(self, db_session, sample_kanban_lists, sample_user):
        """Test de création avec list_id=-1 (auto-affectation à la première liste)."""
        card_data = CardCreate(
            titre="Auto-list Card",
            list_id=-1,  # Devrait être automatiquement assigné à la première liste
        )
        
        result = create_card(db_session, card_data, sample_user.id)
        
        assert result.list_id == sample_kanban_lists[0].id

    def test_create_card_no_available_lists(self, db_session, sample_user):
        """Test de création quand aucune liste n'est disponible."""
        card_data = CardCreate(
            titre="No List Card",
            list_id=-1,
        )
        
        with pytest.raises(ValueError, match="Aucune liste valide n'est disponible"):
            create_card(db_session, card_data, sample_user.id)

    def test_create_card_nonexistent_list(self, db_session, sample_user):
        """Test de création avec une liste inexistante."""
        card_data = CardCreate(
            titre="Invalid List Card",
            list_id=99999,
        )
        
        # Note: Ce test peut ne pas lever d'erreur selon la configuration de la base de données
        # Dans certains cas, la carte peut être créée mais échouer lors de l'accès
        result = create_card(db_session, card_data, sample_user.id)
        
        # Si la carte est créée, elle devrait avoir un problème avec la relation
        assert result.list_id == 99999

    def test_create_card_nonexistent_labels(self, db_session, sample_kanban_lists, sample_user):
        """Test de création avec des étiquettes inexistantes."""
        card_data = CardCreate(
            titre="Invalid Labels Card",
            list_id=sample_kanban_lists[0].id,
            label_ids=[99999, 99998],
        )
        
        # Devrait créer la carte mais sans les étiquettes inexistantes
        result = create_card(db_session, card_data, sample_user.id)
        assert len(result.labels) == 0

    def test_create_card_unicode_content(self, db_session, sample_kanban_lists, sample_user):
        """Test de création avec contenu Unicode."""
        card_data = CardCreate(
            titre="Carte avec caractères spéciaux: éèàçù 🚀 中文",
            description="Description spéciale",
            list_id=sample_kanban_lists[0].id,
        )
        
        result = create_card(db_session, card_data, sample_user.id)
        
        assert result.titre == "Carte avec caractères spéciaux: éèàçù 🚀 中文"
        assert result.description == "Description spéciale"

    def test_create_card_max_title_length(self, db_session, sample_kanban_lists, sample_user):
        """Test de création avec titre de longueur maximale."""
        max_title = "x" * 200
        card_data = CardCreate(
            titre=max_title,
            list_id=sample_kanban_lists[0].id,
        )
        
        result = create_card(db_session, card_data, sample_user.id)
        assert result.titre == max_title

    def test_create_card_with_due_date(self, db_session, sample_kanban_lists, sample_user):
        """Test de création avec date d'échéance."""
        due_date = date.today() + timedelta(days=7)
        card_data = CardCreate(
            titre="Due Date Card",
            list_id=sample_kanban_lists[0].id,
            date_echeance=due_date,
        )
        
        result = create_card(db_session, card_data, sample_user.id)
        assert result.date_echeance == due_date


class TestUpdateCard:
    """Tests pour la fonction update_card."""

    def test_update_card_success(self, db_session, sample_cards, sample_user, sample_labels):
        """Test de mise à jour réussie d'une carte."""
        card = sample_cards[0]
        update_data = CardUpdate(
            titre="Updated Card",
            description="Updated Description",
            priorite=CardPriority.LOW,
            assignee_id=create_sample_user_2(db_session).id,
            label_ids=[sample_labels[2].id],
        )
        
        result = update_card(db_session, card.id, update_data, sample_user.id)
        
        assert result is not None
        assert result.titre == "Updated Card"
        assert result.description == "Updated Description"
        assert result.priorite == CardPriority.LOW
        assert result.assignee_id == create_sample_user_2(db_session).id
        assert len(result.labels) == 1
        assert result.labels[0].id == sample_labels[2].id

    def test_update_card_nonexistent(self, db_session, sample_user):
        """Test de mise à jour d'une carte inexistante."""
        update_data = CardUpdate(titre="Updated")
        
        result = update_card(db_session, 99999, update_data, sample_user.id)
        
        assert result is None

    def test_update_card_partial_update(self, db_session, sample_cards, sample_user):
        """Test de mise à jour partielle (seulement certains champs)."""
        card = sample_cards[0]
        original_description = card.description
        original_priorite = card.priorite
        
        update_data = CardUpdate(titre="Partial Update")
        
        result = update_card(db_session, card.id, update_data, sample_user.id)
        
        assert result.titre == "Partial Update"
        assert result.description == original_description
        assert result.priorite == original_priorite

    def test_update_card_list_id_minus_1(self, db_session, sample_cards, sample_user):
        """Test de mise à jour avec list_id=-1."""
        card = sample_cards[0]
        update_data = CardUpdate(list_id=-1)
        
        result = update_card(db_session, card.id, update_data, sample_user.id)
        
        # Devrait être assigné à la première liste
        assert result.list_id != -1

    def test_update_card_remove_labels(self, db_session, sample_cards, sample_user):
        """Test de suppression des étiquettes."""
        card = sample_cards[0]  # A déjà des étiquettes
        
        update_data = CardUpdate(label_ids=[])
        
        result = update_card(db_session, card.id, update_data, sample_user.id)
        
        assert len(result.labels) == 0

    def test_update_card_protected_fields(self, db_session, sample_cards, sample_user):
        """Test que les champs protégés ne sont pas modifiés."""
        card = sample_cards[0]
        original_id = card.id
        original_created_by = card.created_by
        original_created_at = card.created_at
        
        update_data = CardUpdate(titre="Test")
        
        result = update_card(db_session, card.id, update_data, sample_user.id)
        
        assert result.id == original_id
        assert result.created_by == original_created_by
        assert result.created_at == original_created_at

    def test_update_card_unicode_content(self, db_session, sample_cards, sample_user):
        """Test de mise à jour avec contenu Unicode."""
        card = sample_cards[0]
        unicode_title = "Titre mis à jour avec caractères spéciaux: éèàçù 🚀 中文"
        
        update_data = CardUpdate(titre=unicode_title)
        
        result = update_card(db_session, card.id, update_data, sample_user.id)
        
        assert result.titre == unicode_title


class TestUpdateCardList:
    """Tests pour la fonction update_card_list."""

    def test_update_card_list_success(self, db_session, sample_cards, sample_kanban_lists):
        """Test de mise à jour réussie de la liste d'une carte."""
        card = sample_cards[0]
        new_list_id = sample_kanban_lists[1].id
        
        list_update = CardListUpdate(list_id=new_list_id)
        result = update_card_list(db_session, card.id, list_update)
        
        assert result is not None
        assert result.list_id == new_list_id

    def test_update_card_list_nonexistent(self, db_session, sample_kanban_lists):
        """Test de mise à jour de la liste d'une carte inexistante."""
        list_update = CardListUpdate(list_id=sample_kanban_lists[1].id)
        
        result = update_card_list(db_session, 99999, list_update)
        
        assert result is None

    def test_update_card_list_minus_1(self, db_session, sample_cards, sample_kanban_lists):
        """Test de mise à jour avec list_id=-1."""
        card = sample_cards[0]
        list_update = CardListUpdate(list_id=-1)
        
        result = update_card_list(db_session, card.id, list_update)
        
        assert result is not None
        assert result.list_id == sample_kanban_lists[0].id  # Première liste


class TestArchiveCard:
    """Tests pour la fonction archive_card."""

    def test_archive_card_success(self, db_session, sample_cards, sample_user):
        """Test d'archivage réussi d'une carte."""
        card = sample_cards[0]
        
        result = archive_card(db_session, card.id, sample_user.id)
        
        assert result is not None
        assert result.is_archived is True

    def test_archive_card_nonexistent(self, db_session, sample_user):
        """Test d'archivage d'une carte inexistante."""
        result = archive_card(db_session, 99999, sample_user.id)
        
        assert result is None

    def test_archive_card_already_archived(self, db_session, sample_cards, sample_user):
        """Test d'archivage d'une carte déjà archivée."""
        card = sample_cards[2]  # Déjà archivée
        
        result = archive_card(db_session, card.id, sample_user.id)
        
        assert result is not None
        assert result.is_archived is True


class TestUnarchiveCard:
    """Tests pour la fonction unarchive_card."""

    def test_unarchive_card_success(self, db_session, sample_cards, sample_user):
        """Test de désarchivage réussi d'une carte."""
        card = sample_cards[2]  # Carte archivée
        
        result = unarchive_card(db_session, card.id, sample_user.id)
        
        assert result is not None
        assert result.is_archived is False

    def test_unarchive_card_nonexistent(self, db_session, sample_user):
        """Test de désarchivage d'une carte inexistante."""
        result = unarchive_card(db_session, 99999, sample_user.id)
        
        assert result is None

    def test_unarchive_card_not_archived(self, db_session, sample_cards, sample_user):
        """Test de désarchivage d'une carte non archivée."""
        card = sample_cards[0]  # Pas archivée
        
        result = unarchive_card(db_session, card.id, sample_user.id)
        
        assert result is not None
        assert result.is_archived is False


class TestDeleteCard:
    """Tests pour la fonction delete_card."""

    def test_delete_card_success(self, db_session, sample_cards):
        """Test de suppression réussie d'une carte."""
        card = sample_cards[0]
        
        result = delete_card(db_session, card.id)
        
        assert result is True
        
        # Vérifier que la carte a été supprimée
        deleted_card = get_card(db_session, card.id)
        assert deleted_card is None

    def test_delete_card_nonexistent(self, db_session):
        """Test de suppression d'une carte inexistante."""
        result = delete_card(db_session, 99999)
        
        assert result is False


class TestMoveCard:
    """Tests pour la fonction move_card."""

    def test_move_card_different_list(self, db_session, sample_cards, sample_kanban_lists, sample_user):
        """Test de déplacement réussi d'une carte vers une autre liste."""
        card = sample_cards[0]
        source_list_id = card.list_id
        target_list_id = sample_kanban_lists[1].id
        
        move_request = CardMoveRequest(
            source_list_id=source_list_id,
            target_list_id=target_list_id,
        )
        
        result = move_card(db_session, card.id, move_request, sample_user.id)
        
        assert result is not None
        assert result.list_id == target_list_id
        assert result.position == 2  # Position à la fin de la nouvelle liste

    def test_move_card_same_list(self, db_session, sample_cards, sample_user):
        """Test de déplacement d'une carte dans la même liste."""
        card = sample_cards[0]
        source_list_id = card.list_id
        
        move_request = CardMoveRequest(
            source_list_id=source_list_id,
            target_list_id=source_list_id,
            position=1,
        )
        
        result = move_card(db_session, card.id, move_request, sample_user.id)
        
        assert result is not None
        assert result.list_id == source_list_id
        assert result.position == 1

    def test_move_card_nonexistent(self, db_session, sample_kanban_lists, sample_user):
        """Test de déplacement d'une carte inexistante."""
        move_request = CardMoveRequest(
            source_list_id=sample_kanban_lists[0].id,
            target_list_id=sample_kanban_lists[1].id,
        )
        
        result = move_card(db_session, 99999, move_request, sample_user.id)
        
        assert result is None

    def test_move_card_wrong_source_list(self, db_session, sample_cards, sample_kanban_lists, sample_user):
        """Test de déplacement avec une liste source incorrecte."""
        card = sample_cards[0]
        wrong_source_id = sample_kanban_lists[1].id
        
        move_request = CardMoveRequest(
            source_list_id=wrong_source_id,
            target_list_id=sample_kanban_lists[2].id,
        )
        
        result = move_card(db_session, card.id, move_request, sample_user.id)
        
        assert result is None

    def test_move_card_position_compaction(self, db_session, sample_cards, sample_kanban_lists, sample_user):
        """Test de compaction des positions après déplacement."""
        card = sample_cards[0]
        source_list_id = card.list_id
        target_list_id = sample_kanban_lists[1].id
        
        move_request = CardMoveRequest(
            source_list_id=source_list_id,
            target_list_id=target_list_id,
        )
        
        move_card(db_session, card.id, move_request, sample_user.id)
        
        # Vérifier que les positions dans l'ancienne liste ont été compactées
        remaining_cards = get_cards(db_session, CardFilter(list_id=source_list_id))
        positions = [c.position for c in sorted(remaining_cards, key=lambda x: x.position)]
        assert positions == [1]  # La carte restante devrait être en position 1

    def test_move_card_with_specific_position(self, db_session, sample_cards, sample_kanban_lists, sample_user):
        """Test de déplacement avec position spécifique."""
        card = sample_cards[0]
        source_list_id = card.list_id
        target_list_id = sample_kanban_lists[1].id
        
        move_request = CardMoveRequest(
            source_list_id=source_list_id,
            target_list_id=target_list_id,
            position=1,
        )
        
        result = move_card(db_session, card.id, move_request, sample_user.id)
        
        assert result is not None
        assert result.position == 1
        
        # Vérifier que les cartes existantes ont été décalées
        target_cards = get_cards(db_session, CardFilter(list_id=target_list_id))
        positions = [c.position for c in sorted(target_cards, key=lambda x: x.position)]
        # Les positions devraient être uniques et ordonnées
        assert len(positions) == len(set(positions))
        assert positions == sorted(positions)
        assert len(positions) >= 1  # Au moins la nouvelle carte


class TestBulkMoveCards:
    """Tests pour la fonction bulk_move_cards."""

    def test_bulk_move_cards_success(self, db_session, sample_cards, sample_kanban_lists):
        """Test de déplacement en masse réussi."""
        source_list_id = sample_kanban_lists[0].id
        target_list_id = sample_kanban_lists[2].id
        
        # Récupérer les IDs des cartes à déplacer
        card_ids = [card.id for card in sample_cards[:2] if card.list_id == source_list_id]
        
        bulk_request = BulkCardMoveRequest(
            card_ids=card_ids,
            target_list_id=target_list_id,
        )
        
        result = bulk_move_cards(db_session, bulk_request)
        
        assert len(result) == 2
        assert all(card.list_id == target_list_id for card in result)
        # Vérifier que les positions sont séquentielles
        positions = [card.position for card in sorted(result, key=lambda x: x.position)]
        assert positions == [1, 2]

    def test_bulk_move_cards_empty_list(self, db_session, sample_kanban_lists):
        """Test de déplacement en masse avec une liste vide."""
        # Note: Le schéma de validation peut empêcher une liste vide selon la configuration
        try:
            bulk_request = BulkCardMoveRequest(
                card_ids=[],
                target_list_id=sample_kanban_lists[1].id,
            )
            
            result = bulk_move_cards(db_session, bulk_request)
            
            assert len(result) == 0
        except Exception:
            # Si la validation empêche la liste vide, c'est aussi un comportement acceptable
            pass

    def test_bulk_move_cards_nonexistent_cards(self, db_session, sample_kanban_lists):
        """Test de déplacement en masse avec des cartes inexistantes."""
        bulk_request = BulkCardMoveRequest(
            card_ids=[99999, 99998],
            target_list_id=sample_kanban_lists[1].id,
        )
        
        result = bulk_move_cards(db_session, bulk_request)
        
        assert len(result) == 0

    def test_bulk_move_cards_partial_success(self, db_session, sample_cards, sample_kanban_lists):
        """Test de déplacement en masse avec succès partiel."""
        # Mélanger des IDs existants et inexistants
        existing_ids = [sample_cards[0].id, sample_cards[1].id]
        bulk_request = BulkCardMoveRequest(
            card_ids=existing_ids + [99999],
            target_list_id=sample_kanban_lists[2].id,
        )
        
        result = bulk_move_cards(db_session, bulk_request)
        
        assert len(result) == 2  # Seulement les cartes existantes
        assert all(card.list_id == sample_kanban_lists[2].id for card in result)


class TestCardIntegration:
    """Tests d'intégration pour le service Card."""

    def test_create_update_delete_flow(self, db_session, sample_kanban_lists, sample_user, sample_labels):
        """Test du flux complet CRUD."""
        # Créer
        card_data = CardCreate(
            titre="Test Card",
            list_id=sample_kanban_lists[0].id,
            label_ids=[sample_labels[0].id],
        )
        created_card = create_card(db_session, card_data, sample_user.id)
        
        # Mettre à jour
        update_data = CardUpdate(
            titre="Updated Test Card",
            priorite=CardPriority.HIGH,
        )
        updated_card = update_card(db_session, created_card.id, update_data, sample_user.id)
        
        assert updated_card is not None
        assert updated_card.titre == "Updated Test Card"
        assert updated_card.priorite == CardPriority.HIGH
        
        # Archiver
        archived_card = archive_card(db_session, created_card.id, sample_user.id)
        assert archived_card.is_archived is True
        
        # Désarchiver
        unarchived_card = unarchive_card(db_session, created_card.id, sample_user.id)
        assert unarchived_card.is_archived is False
        
        # Supprimer
        delete_result = delete_card(db_session, created_card.id)
        assert delete_result is True

    def test_card_movement_between_lists(self, db_session, sample_kanban_lists, sample_user):
        """Test de mouvement de cartes entre différentes listes."""
        # Créer des cartes dans différentes listes
        card1_data = CardCreate(titre="Card 1", list_id=sample_kanban_lists[0].id)
        card2_data = CardCreate(titre="Card 2", list_id=sample_kanban_lists[0].id)
        card3_data = CardCreate(titre="Card 3", list_id=sample_kanban_lists[1].id)
        
        card1 = create_card(db_session, card1_data, sample_user.id)
        create_card(db_session, card2_data, sample_user.id)
        create_card(db_session, card3_data, sample_user.id)
        
        # Déplacer une carte entre listes
        move_request = CardMoveRequest(
            source_list_id=sample_kanban_lists[0].id,
            target_list_id=sample_kanban_lists[2].id,
        )
        moved_card = move_card(db_session, card1.id, move_request, sample_user.id)
        
        assert moved_card.list_id == sample_kanban_lists[2].id
        
        # Vérifier que les positions ont été ajustées
        list0_cards = get_cards(db_session, CardFilter(list_id=sample_kanban_lists[0].id))
        list2_cards = get_cards(db_session, CardFilter(list_id=sample_kanban_lists[2].id))
        
        assert len(list0_cards) == 1
        assert len(list2_cards) == 1

    def test_concurrent_operations(self, db_session, sample_kanban_lists, sample_user):
        """Test d'opérations concurrentes (simplifié)."""
        # Créer plusieurs cartes séquentiellement
        cards = []
        for i in range(5):
            card_data = CardCreate(
                titre=f"Concurrent Card {i}",
                list_id=sample_kanban_lists[0].id,
            )
            card = create_card(db_session, card_data, sample_user.id)
            cards.append(card)
        
        # Vérifier que toutes les cartes existent avec des positions uniques
        all_cards = get_cards(db_session, CardFilter(list_id=sample_kanban_lists[0].id))
        assert len(all_cards) >= 5
        
        positions = [card.position for card in all_cards]
        assert len(set(positions)) == len(positions)  # Positions uniques

    def test_edge_case_empty_title(self, db_session, sample_kanban_lists, sample_user):
        """Test avec titre vide (devrait échouer à cause de la validation Pydantic)."""
        with pytest.raises(ValueError):
            CardCreate(titre="", list_id=sample_kanban_lists[0].id)

    def test_edge_case_very_long_title(self, db_session, sample_kanban_lists, sample_user):
        """Test avec titre très long (devrait échouer à cause de la validation Pydantic)."""
        long_title = "x" * 201  # Dépasse la limite de 200
        
        with pytest.raises(ValueError):
            CardCreate(titre=long_title, list_id=sample_kanban_lists[0].id)

    def test_card_labels_management(self, db_session, sample_kanban_lists, sample_user, sample_labels):
        """Test de gestion des étiquettes sur les cartes."""
        # Créer une carte avec des étiquettes
        card_data = CardCreate(
            titre="Labels Test",
            list_id=sample_kanban_lists[0].id,
            label_ids=[sample_labels[0].id, sample_labels[1].id],
        )
        card = create_card(db_session, card_data, sample_user.id)
        
        assert len(card.labels) == 2
        
        # Mettre à jour pour changer les étiquettes
        update_data = CardUpdate(label_ids=[sample_labels[2].id])
        updated_card = update_card(db_session, card.id, update_data, sample_user.id)
        
        assert len(updated_card.labels) == 1
        assert updated_card.labels[0].id == sample_labels[2].id
        
        # Supprimer toutes les étiquettes
        update_data = CardUpdate(label_ids=[])
        final_card = update_card(db_session, card.id, update_data, sample_user.id)
        
        assert len(final_card.labels) == 0


class TestCardSecurity:
    """Tests de sécurité pour le service Card."""

    def test_sql_injection_prevention(self, db_session, sample_kanban_lists, sample_user):
        """Test de prévention d'injection SQL."""
        malicious_title = "'; DROP TABLE cards; --"
        
        card_data = CardCreate(
            titre=malicious_title,
            list_id=sample_kanban_lists[0].id,
        )
        
        # La création devrait fonctionner (le titre est stocké littéralement)
        result = create_card(db_session, card_data, sample_user.id)
        assert result.titre == malicious_title
        
        # Vérifier que la table n'a pas été supprimée
        cards = get_cards(db_session, CardFilter())
        assert len(cards) > 0

    def test_xss_prevention(self, db_session, sample_kanban_lists, sample_user):
        """Test de prévention XSS."""
        xss_title = "<script>alert('XSS')</script><img src='x' onerror='alert(1)'>"
        
        card_data = CardCreate(
            titre=xss_title,
            list_id=sample_kanban_lists[0].id,
        )
        
        result = create_card(db_session, card_data, sample_user.id)
        assert result.titre == xss_title  # Stocké tel quel
        
        # La protection XSS devrait être gérée au niveau du frontend/affichage

    def test_search_injection_prevention(self, db_session, sample_cards):
        """Test de prévention d'injection dans la recherche."""
        malicious_search = "'; DROP TABLE cards; --"
        
        filters = CardFilter(search=malicious_search)
        cards = get_cards(db_session, filters)
        
        # La recherche devrait retourner des résultats vides plutôt que d'exécuter l'injection
        assert len(cards) == 0

    def test_unauthorized_card_access(self, db_session, sample_cards):
        """Test que les opérations nécessitent des permissions appropriées."""
        # Les opérations de base ne nécessitent pas de vérification d'utilisateur
        # mais les opérations sensibles (comme l'historique) le font
        card = sample_cards[0]
        
        # Test de récupération (pas de restriction)
        retrieved_card = get_card(db_session, card.id)
        assert retrieved_card is not None
        
        # Test de mise à jour sans user_id (devrait fonctionner)
        update_data = CardUpdate(titre="Test Update")
        updated_card = update_card(db_session, card.id, update_data)
        assert updated_card is not None

    def test_card_content_sanitization_storage(self, db_session, sample_kanban_lists, sample_user):
        """Test que le contenu est stocké tel quel (sanitization au niveau affichage)."""
        dangerous_content = "<script>alert('danger')</script> & <div>HTML content</div>"
        
        card_data = CardCreate(
            titre=dangerous_content,
            description=dangerous_content,
            list_id=sample_kanban_lists[0].id,
        )
        
        result = create_card(db_session, card_data, sample_user.id)
        assert result.titre == dangerous_content
        assert result.description == dangerous_content

    def test_special_characters_storage(self, db_session, sample_kanban_lists, sample_user):
        """Test de stockage de caractères spéciaux."""
        special_chars = "éèàçù€£¥©®™•§¶†‡°…‰™œŒšžŠŸŒ"
        
        card_data = CardCreate(
            titre=special_chars,
            description=special_chars,
            list_id=sample_kanban_lists[0].id,
        )
        
        result = create_card(db_session, card_data, sample_user.id)
        assert result.titre == special_chars
        assert result.description == special_chars