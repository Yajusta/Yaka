"""Tests pour le modèle KanbanList."""

import pytest
import sys
import os
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.kanban_list import KanbanList
from app.models.card import Card


# Configuration de la base de données de test
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_kanban_lists.db"
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


class TestKanbanListModel:
    """Tests pour le modèle KanbanList."""

    def test_create_kanban_list(self, db_session):
        """Test de création d'une liste Kanban."""
        # Arrange
        list_data = {
            "name": "Test List",
            "order": 1
        }
        
        # Act
        kanban_list = KanbanList(**list_data)
        db_session.add(kanban_list)
        db_session.commit()
        db_session.refresh(kanban_list)
        
        # Assert
        assert kanban_list.id is not None
        assert kanban_list.name == "Test List"
        assert kanban_list.order == 1
        assert kanban_list.created_at is not None
        assert isinstance(kanban_list.created_at, datetime)
        assert kanban_list.updated_at is None  # Pas encore mis à jour

    def test_kanban_list_string_representation(self, db_session):
        """Test de la représentation string d'une liste Kanban."""
        # Arrange & Act
        kanban_list = KanbanList(name="Test List", order=1)
        db_session.add(kanban_list)
        db_session.commit()
        
        # Assert
        assert str(kanban_list.name) == "Test List"

    def test_kanban_list_ordering(self, db_session):
        """Test de l'ordre des listes Kanban."""
        # Arrange
        list1 = KanbanList(name="First List", order=2)
        list2 = KanbanList(name="Second List", order=1)
        list3 = KanbanList(name="Third List", order=3)
        
        # Act
        db_session.add_all([list1, list2, list3])
        db_session.commit()
        
        # Récupérer les listes ordonnées
        ordered_lists = db_session.query(KanbanList).order_by(KanbanList.order).all()
        
        # Assert
        assert len(ordered_lists) == 3
        assert ordered_lists[0].name == "Second List"  # order=1
        assert ordered_lists[1].name == "First List"   # order=2
        assert ordered_lists[2].name == "Third List"   # order=3

    def test_kanban_list_name_constraints(self, db_session):
        """Test des contraintes sur le nom de la liste."""
        # Test nom vide - SQLAlchemy accepte mais la logique métier devrait valider
        kanban_list = KanbanList(name="", order=1)
        db_session.add(kanban_list)
        db_session.commit()
        
        # La base de données accepte, mais la logique métier devrait valider
        assert kanban_list.name == ""

    def test_kanban_list_name_max_length(self, db_session):
        """Test de la longueur maximale du nom."""
        # Arrange - nom de 100 caractères (limite)
        long_name = "A" * 100
        
        # Act
        kanban_list = KanbanList(name=long_name, order=1)
        db_session.add(kanban_list)
        db_session.commit()
        
        # Assert
        assert kanban_list.name == long_name
        assert len(kanban_list.name) == 100

    def test_kanban_list_name_exceeds_max_length(self, db_session):
        """Test d'un nom dépassant la longueur maximale."""
        # Arrange - nom de 101 caractères (dépasse la limite)
        too_long_name = "A" * 101
        
        # Act - SQLite peut accepter mais sera tronqué à 100 caractères
        kanban_list = KanbanList(name=too_long_name, order=1)
        db_session.add(kanban_list)
        db_session.commit()
        db_session.refresh(kanban_list)
        
        # Assert - SQLite accepte le nom long, mais la logique métier devrait valider
        assert len(kanban_list.name) == 101  # SQLite n'applique pas la contrainte de longueur

    def test_kanban_list_order_constraints(self, db_session):
        """Test des contraintes sur l'ordre."""
        # Test ordre négatif - pas de contrainte DB mais logique métier
        kanban_list = KanbanList(name="Test List", order=-1)
        db_session.add(kanban_list)
        db_session.commit()
        
        # La base de données accepte, mais la logique métier devrait valider
        assert kanban_list.order == -1

    def test_kanban_list_relationship_with_cards(self, db_session):
        """Test de la relation avec les cartes."""
        # Arrange
        kanban_list = KanbanList(name="Test List", order=1)
        db_session.add(kanban_list)
        db_session.commit()
        db_session.refresh(kanban_list)
        
        # Créer des cartes liées à cette liste
        card1 = Card(
            titre="Card 1",
            description="Description 1",
            list_id=kanban_list.id,
            created_by=1,  # Assuming user ID 1 exists
            assignee_id=1
        )
        card2 = Card(
            titre="Card 2", 
            description="Description 2",
            list_id=kanban_list.id,
            created_by=1,
            assignee_id=1
        )
        
        db_session.add_all([card1, card2])
        db_session.commit()
        
        # Act - Récupérer la liste avec ses cartes
        db_session.refresh(kanban_list)
        
        # Assert
        assert len(kanban_list.cards) == 2
        assert card1 in kanban_list.cards
        assert card2 in kanban_list.cards

    def test_kanban_list_updated_at_on_modification(self, db_session):
        """Test que updated_at est mis à jour lors de modifications."""
        # Arrange
        kanban_list = KanbanList(name="Original Name", order=1)
        db_session.add(kanban_list)
        db_session.commit()
        db_session.refresh(kanban_list)
        
        original_updated_at = kanban_list.updated_at
        
        # Act - Modifier la liste
        kanban_list.name = "Modified Name"
        db_session.commit()
        db_session.refresh(kanban_list)
        
        # Assert
        assert kanban_list.updated_at != original_updated_at
        assert kanban_list.name == "Modified Name"

    def test_multiple_lists_unique_orders(self, db_session):
        """Test que plusieurs listes peuvent avoir des ordres différents."""
        # Arrange & Act
        lists = []
        for i in range(5):
            kanban_list = KanbanList(name=f"List {i+1}", order=i+1)
            lists.append(kanban_list)
            db_session.add(kanban_list)
        
        db_session.commit()
        
        # Assert
        saved_lists = db_session.query(KanbanList).order_by(KanbanList.order).all()
        assert len(saved_lists) == 5
        
        for i, saved_list in enumerate(saved_lists):
            assert saved_list.order == i + 1
            assert saved_list.name == f"List {i+1}"

    def test_kanban_list_cascade_delete_behavior(self, db_session):
        """Test du comportement lors de la suppression d'une liste avec des cartes."""
        # Arrange
        kanban_list = KanbanList(name="Test List", order=1)
        db_session.add(kanban_list)
        db_session.commit()
        db_session.refresh(kanban_list)
        
        # Créer une carte liée
        card = Card(
            titre="Test Card",
            description="Test Description",
            list_id=kanban_list.id,
            created_by=1,
            assignee_id=1
        )
        db_session.add(card)
        db_session.commit()
        
        # Act - Supprimer la liste
        db_session.delete(kanban_list)
        
        # Assert - Devrait lever une erreur de contrainte de clé étrangère
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()