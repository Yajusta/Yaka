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
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_card_positions.db"
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
        assert card1.position == 1
        assert card2.position == 2
        assert card3.position == 3

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
        assert cards[0].title == "Carte A" and cards[0].position == 1
        assert cards[1].title == "Carte B" and cards[1].position == 2
        assert cards[2].title == "Carte C" and cards[2].position == 3

    def test_move_card_to_first_position_same_list(self, db_session, test_user, test_list):
        """Test déplacer une carte en première position dans la même liste."""
        # Créer 3 cartes
        card1 = create_card(db_session, CardCreate(title="Carte 1", list_id=test_list.id), test_user.id)
        card2 = create_card(db_session, CardCreate(title="Carte 2", list_id=test_list.id), test_user.id)
        card3 = create_card(db_session, CardCreate(title="Carte 3", list_id=test_list.id), test_user.id)
        
        # Déplacer la carte 3 en première position
        move_card(db_session, card3.id, CardMoveRequest(
            source_list_id=test_list.id,
            target_list_id=test_list.id,
            position=1
        ))
        
        # Récupérer les cartes dans l'ordre
        cards = get_cards(db_session, CardFilter(list_id=test_list.id))
        
        # Vérifier le nouvel ordre
        assert cards[0].id == card3.id and cards[0].position == 1
        assert cards[1].id == card1.id and cards[1].position == 2
        assert cards[2].id == card2.id and cards[2].position == 3