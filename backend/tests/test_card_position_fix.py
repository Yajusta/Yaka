"""Tests pour vérifier que le problème de position des cartes est résolu."""

import pytest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.card import Card
from app.models.kanban_list import KanbanList
from app.models.user import User
from app.services.card import create_card, move_card, get_cards
from app.schemas.card import CardCreate, CardMoveRequest, CardFilter

# Configuration de la base de données de test
TEST_DB_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(TEST_DB_DIR, exist_ok=True)
TEST_DB_PATH = os.path.join(TEST_DB_DIR, "test_card_positions.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"
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
def test_user(db_session):
    """Fixture pour créer un utilisateur de test."""
    user = User(email="test@example.com", password_hash="test", display_name="Test User")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_list(db_session):
    """Fixture pour créer une liste de test."""
    kanban_list = KanbanList(name="Test List", order=1)
    db_session.add(kanban_list)
    db_session.commit()
    db_session.refresh(kanban_list)
    return kanban_list


class TestCardPositionFix:
    """Tests pour la correction du problème de position des cartes."""

    def test_new_cards_get_correct_positions(self, db_session, test_user, test_list):
        """Test que les nouvelles cartes reçoivent des positions correctes."""
        # Créer 3 cartes
        card1 = create_card(db_session, CardCreate(
            title="Carte 1", 
            list_id=test_list.id
        ), test_user.id)
        
        card2 = create_card(db_session, CardCreate(
            title="Carte 2", 
            list_id=test_list.id
        ), test_user.id)
        
        card3 = create_card(db_session, CardCreate(
            title="Carte 3", 
            list_id=test_list.id
        ), test_user.id)
        
        # Vérifier les positions
        assert card1.position == 0
        assert card2.position == 1
        assert card3.position == 2

    def test_cards_are_retrieved_in_position_order(self, db_session, test_user, test_list):
        """Test que les cartes sont récupérées dans l'ordre de position."""
        # Créer 3 cartes
        create_card(db_session, CardCreate(title="Carte A", list_id=test_list.id), test_user.id)
        create_card(db_session, CardCreate(title="Carte B", list_id=test_list.id), test_user.id)
        create_card(db_session, CardCreate(title="Carte C", list_id=test_list.id), test_user.id)
        
        # Récupérer les cartes
        cards = get_cards(db_session, CardFilter(list_id=test_list.id))
        
        # Vérifier l'ordre
        assert len(cards) == 3
        assert cards[0].title == "Carte A" and cards[0].position == 0
        assert cards[1].title == "Carte B" and cards[1].position == 1
        assert cards[2].title == "Carte C" and cards[2].position == 2

    def test_move_card_to_first_position_same_list(self, db_session, test_user, test_list):
        """Test déplacer une carte en première position dans la même liste."""
        # Créer 3 cartes
        card1 = create_card(db_session, CardCreate(title="Carte 1", list_id=test_list.id), test_user.id)
        card2 = create_card(db_session, CardCreate(title="Carte 2", list_id=test_list.id), test_user.id)
        card3 = create_card(db_session, CardCreate(title="Carte 3", list_id=test_list.id), test_user.id)

        # Déplacer la carte 3 en première position (position 0)
        move_card(db_session, card3.id, CardMoveRequest(
            source_list_id=test_list.id,
            target_list_id=test_list.id,
            position=0
        ))

        # Récupérer les cartes dans l'ordre
        cards = get_cards(db_session, CardFilter(list_id=test_list.id))

        # Vérifier que les positions sont normalisées (0, 1, 2)
        positions = [card.position for card in cards]
        assert positions == [0, 1, 2], f"Positions attendues: [0, 1, 2], obtenues: {positions}"

        # Vérifier que card3 est en première position
        assert cards[0].id == card3.id and cards[0].position == 0
        assert cards[1].id == card1.id and cards[1].position == 1
        assert cards[2].id == card2.id and cards[2].position == 2

    def test_move_card_to_last_position_same_list(self, db_session, test_user, test_list):
        """Test déplacer une carte en dernière position dans la même liste."""
        # Créer 3 cartes
        card1 = create_card(db_session, CardCreate(title="Carte 1", list_id=test_list.id), test_user.id)
        card2 = create_card(db_session, CardCreate(title="Carte 2", list_id=test_list.id), test_user.id)
        card3 = create_card(db_session, CardCreate(title="Carte 3", list_id=test_list.id), test_user.id)

        # Déplacer la carte 1 en dernière position (position 2)
        move_card(db_session, card1.id, CardMoveRequest(
            source_list_id=test_list.id,
            target_list_id=test_list.id,
            position=2
        ))

        # Récupérer les cartes dans l'ordre
        cards = get_cards(db_session, CardFilter(list_id=test_list.id))

        # Vérifier que les positions sont normalisées (0, 1, 2)
        positions = [card.position for card in cards]
        assert positions == [0, 1, 2], f"Positions attendues: [0, 1, 2], obtenues: {positions}"

        # Vérifier que card1 est en dernière position
        assert cards[0].id == card2.id and cards[0].position == 0
        assert cards[1].id == card3.id and cards[1].position == 1
        assert cards[2].id == card1.id and cards[2].position == 2

    def test_positions_are_normalized_after_card_deletion(self, db_session, test_user, test_list):
        """Test que les positions sont normalisées après suppression d'une carte."""
        # Créer 4 cartes
        card1 = create_card(db_session, CardCreate(title="Carte 1", list_id=test_list.id), test_user.id)
        card2 = create_card(db_session, CardCreate(title="Carte 2", list_id=test_list.id), test_user.id)
        card3 = create_card(db_session, CardCreate(title="Carte 3", list_id=test_list.id), test_user.id)
        card4 = create_card(db_session, CardCreate(title="Carte 4", list_id=test_list.id), test_user.id)

        # Supprimer la deuxième carte
        from app.services.card import delete_card
        delete_card(db_session, card2.id)

        # Récupérer les cartes dans l'ordre
        cards = get_cards(db_session, CardFilter(list_id=test_list.id))

        # Vérifier que les positions sont normalisées (0, 1, 2)
        positions = [card.position for card in cards]
        assert positions == [0, 1, 2], f"Positions attendues: [0, 1, 2], obtenues: {positions}"

        # Vérifier l'ordre des cartes restantes
        assert cards[0].id == card1.id and cards[0].position == 0
        assert cards[1].id == card3.id and cards[1].position == 1
        assert cards[2].id == card4.id and cards[2].position == 2

    def test_move_card_up_without_duplicate_positions(self, db_session, test_user, test_list):
        """Test déplacer une carte vers le haut sans créer de positions en double."""
        # Créer 4 cartes avec positions normalisées
        card1 = create_card(db_session, CardCreate(title="Carte 1", list_id=test_list.id), test_user.id)
        card2 = create_card(db_session, CardCreate(title="Carte 2", list_id=test_list.id), test_user.id)
        card3 = create_card(db_session, CardCreate(title="Carte 3", list_id=test_list.id), test_user.id)
        card4 = create_card(db_session, CardCreate(title="Carte 4", list_id=test_list.id), test_user.id)

        # Vérifier les positions initiales
        cards = get_cards(db_session, CardFilter(list_id=test_list.id))
        positions = [card.position for card in cards]
        assert positions == [0, 1, 2, 3], f"Positions initiales incorrectes: {positions}"

        # Déplacer la carte en position 3 (card4) vers la position 1
        # Les cartes en position 1 et 2 devraient être décalées vers le bas
        move_card(db_session, card4.id, CardMoveRequest(
            source_list_id=test_list.id,
            target_list_id=test_list.id,
            position=1
        ))

        # Récupérer les cartes et vérifier les positions
        cards = get_cards(db_session, CardFilter(list_id=test_list.id))
        positions = [card.position for card in cards]

        # Vérifier que les positions sont normalisées (0, 1, 2, 3)
        assert positions == [0, 1, 2, 3], f"Positions après déplacement: {positions}"

        # Vérifier l'ordre attendu :
        # card1 (position 0), card4 (position 1), card2 (position 2), card3 (position 3)
        expected_order = [card1.id, card4.id, card2.id, card3.id]
        actual_order = [card.id for card in cards]
        assert actual_order == expected_order, f"Ordre attendu: {expected_order}, obtenu: {actual_order}"

    def test_archived_cards_dont_affect_positions(self, db_session, test_user, test_list):
        """Test que les cartes archivées n'affectent pas les positions des cartes actives."""
        # Créer 3 cartes
        card1 = create_card(db_session, CardCreate(title="Carte 1", list_id=test_list.id), test_user.id)
        card2 = create_card(db_session, CardCreate(title="Carte 2", list_id=test_list.id), test_user.id)
        card3 = create_card(db_session, CardCreate(title="Carte 3", list_id=test_list.id), test_user.id)

        # Archiver la deuxième carte
        from app.services.card import archive_card
        archive_card(db_session, card2.id, test_user.id)

        # Créer une nouvelle carte - elle devrait obtenir la position 1 (pas 3)
        card4 = create_card(db_session, CardCreate(title="Carte 4", list_id=test_list.id), test_user.id)

        # Récupérer les cartes actives (non archivées)
        cards = get_cards(db_session, CardFilter(list_id=test_list.id, include_archived=False))

        # Vérifier que les positions sont séquentielles (0, 1, 2)
        positions = [card.position for card in cards]
        assert positions == [0, 1, 2], f"Positions attendues: [0, 1, 2], obtenues: {positions}"

        # Vérifier l'ordre : card1 (0), card3 (1), card4 (2) - la nouvelle carte va à la fin
        expected_order = [card1.id, card3.id, card4.id]
        actual_order = [card.id for card in cards]
        assert actual_order == expected_order, f"Ordre attendu: {expected_order}, obtenu: {actual_order}"

    def test_move_card_between_lists_with_specific_position(self, db_session, test_user, test_list):
        """Test déplacer une carte vers une autre liste avec une position spécifique."""
        # Créer une deuxième liste
        from app.models.kanban_list import KanbanList
        target_list = KanbanList(name="Target List", order=2)
        db_session.add(target_list)
        db_session.commit()
        db_session.refresh(target_list)

        # Créer 3 cartes dans la liste source
        card1 = create_card(db_session, CardCreate(title="Source 1", list_id=test_list.id), test_user.id)
        card2 = create_card(db_session, CardCreate(title="Source 2", list_id=test_list.id), test_user.id)
        card3 = create_card(db_session, CardCreate(title="Source 3", list_id=test_list.id), test_user.id)

        # Créer 3 cartes dans la liste cible
        card4 = create_card(db_session, CardCreate(title="Target 1", list_id=target_list.id), test_user.id)
        card5 = create_card(db_session, CardCreate(title="Target 2", list_id=target_list.id), test_user.id)
        card6 = create_card(db_session, CardCreate(title="Target 3", list_id=target_list.id), test_user.id)

        # Déplacer card2 vers la liste cible à la position 1
        move_card(db_session, card2.id, CardMoveRequest(
            source_list_id=test_list.id,
            target_list_id=target_list.id,
            position=1
        ))

        # Vérifier les cartes dans la liste source (devrait avoir card1, card3 avec positions 0, 1)
        source_cards = get_cards(db_session, CardFilter(list_id=test_list.id))
        source_positions = [card.position for card in source_cards]
        assert source_positions == [0, 1], f"Positions source: {source_positions}"
        source_order = [card.id for card in source_cards]
        assert source_order == [card1.id, card3.id], f"Ordre source: {source_order}"

        # Vérifier les cartes dans la liste cible
        # Devrait avoir: Target 1 (pos 0), Source 2 (pos 1), Target 2 (pos 2), Target 3 (pos 3)
        target_cards = get_cards(db_session, CardFilter(list_id=target_list.id))
        target_positions = [card.position for card in target_cards]
        assert target_positions == [0, 1, 2, 3], f"Positions cible: {target_positions}"
        target_order = [card.id for card in target_cards]
        assert target_order == [card4.id, card2.id, card5.id, card6.id], f"Ordre cible: {target_order}"