"""Tests pour le service KanbanList."""

import pytest
import sys
import os
from unittest.mock import Mock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.kanban_list import KanbanList
from app.models.card import Card
from app.schemas.kanban_list import KanbanListCreate, KanbanListUpdate
from app.services.kanban_list import KanbanListService


# Configuration de la base de données de test
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_kanban_list_service.db"
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
def sample_lists(db_session):
    """Fixture pour créer des listes d'exemple."""
    lists = [
        KanbanList(name="A faire", order=1),
        KanbanList(name="En cours", order=2),
        KanbanList(name="Terminé", order=3)
    ]
    
    for lst in lists:
        db_session.add(lst)
    db_session.commit()
    
    for lst in lists:
        db_session.refresh(lst)
    
    return lists


class TestKanbanListService:
    """Tests pour le service KanbanListService."""

    def test_get_lists_empty(self, db_session):
        """Test de récupération des listes quand aucune n'existe."""
        # Act
        lists = KanbanListService.get_lists(db_session)
        
        # Assert
        assert lists == []

    def test_get_lists_ordered(self, db_session, sample_lists):
        """Test de récupération des listes ordonnées."""
        # Act
        lists = KanbanListService.get_lists(db_session)
        
        # Assert
        assert len(lists) == 3
        assert lists[0].name == "A faire"
        assert lists[0].order == 1
        assert lists[1].name == "En cours"
        assert lists[1].order == 2
        assert lists[2].name == "Terminé"
        assert lists[2].order == 3

    def test_get_list_existing(self, db_session, sample_lists):
        """Test de récupération d'une liste existante."""
        # Arrange
        list_id = sample_lists[0].id
        
        # Act
        result = KanbanListService.get_list(db_session, list_id)
        
        # Assert
        assert result is not None
        assert result.id == list_id
        assert result.name == "A faire"

    def test_get_list_non_existing(self, db_session):
        """Test de récupération d'une liste inexistante."""
        # Act
        result = KanbanListService.get_list(db_session, 999)
        
        # Assert
        assert result is None

    def test_get_list_with_cards_count_no_cards(self, db_session, sample_lists):
        """Test de récupération d'une liste avec comptage des cartes (aucune carte)."""
        # Arrange
        list_id = sample_lists[0].id
        
        # Act
        kanban_list, cards_count = KanbanListService.get_list_with_cards_count(db_session, list_id)
        
        # Assert
        assert kanban_list is not None
        assert kanban_list.id == list_id
        assert cards_count == 0

    def test_get_list_with_cards_count_with_cards(self, db_session, sample_lists):
        """Test de récupération d'une liste avec comptage des cartes (avec cartes)."""
        # Arrange
        list_id = sample_lists[0].id
        
        # Créer des cartes dans cette liste
        cards = [
            Card(titre="Card 1", description="Desc 1", list_id=list_id, created_by=1, assignee_id=1),
            Card(titre="Card 2", description="Desc 2", list_id=list_id, created_by=1, assignee_id=1),
            Card(titre="Card 3", description="Desc 3", list_id=list_id, created_by=1, assignee_id=1)
        ]
        
        for card in cards:
            db_session.add(card)
        db_session.commit()
        
        # Act
        kanban_list, cards_count = KanbanListService.get_list_with_cards_count(db_session, list_id)
        
        # Assert
        assert kanban_list is not None
        assert kanban_list.id == list_id
        assert cards_count == 3

    def test_get_list_with_cards_count_invalid_id(self, db_session):
        """Test avec un ID invalide."""
        # Act & Assert
        with pytest.raises(ValueError, match="L'ID de la liste doit être un entier positif"):
            KanbanListService.get_list_with_cards_count(db_session, 0)
        
        with pytest.raises(ValueError, match="L'ID de la liste doit être un entier positif"):
            KanbanListService.get_list_with_cards_count(db_session, -1)

    def test_get_list_with_cards_count_non_existing(self, db_session):
        """Test avec une liste inexistante."""
        # Act
        kanban_list, cards_count = KanbanListService.get_list_with_cards_count(db_session, 999)

        # Assert
        assert kanban_list is None
        assert cards_count == 0

    def test_get_list_with_cards_count_only_active_cards(self, db_session, sample_lists):
        """Test que get_list_with_cards_count ne compte que les cartes actives (non archivées)."""
        # Arrange
        list_id = sample_lists[0].id

        # Créer des cartes : certaines actives, certaines archivées
        active_cards = [
            Card(titre="Active Card 1", description="Active", list_id=list_id, created_by=1, assignee_id=1, is_archived=False),
            Card(titre="Active Card 2", description="Active", list_id=list_id, created_by=1, assignee_id=1, is_archived=False)
        ]

        archived_cards = [
            Card(titre="Archived Card 1", description="Archived", list_id=list_id, created_by=1, assignee_id=1, is_archived=True),
            Card(titre="Archived Card 2", description="Archived", list_id=list_id, created_by=1, assignee_id=1, is_archived=True),
            Card(titre="Archived Card 3", description="Archived", list_id=list_id, created_by=1, assignee_id=1, is_archived=True)
        ]

        all_cards = active_cards + archived_cards
        for card in all_cards:
            db_session.add(card)
        db_session.commit()

        # Act
        kanban_list, cards_count = KanbanListService.get_list_with_cards_count(db_session, list_id)

        # Assert
        assert kanban_list is not None
        assert kanban_list.id == list_id
        # Doit compter seulement les cartes actives (2 cartes)
        assert cards_count == 2

        # Vérification supplémentaire : compter manuellement pour s'assurer
        total_cards = db_session.query(Card).filter(Card.list_id == list_id).count()
        active_cards_count = db_session.query(Card).filter(Card.list_id == list_id, Card.is_archived == False).count()
        archived_cards_count = db_session.query(Card).filter(Card.list_id == list_id, Card.is_archived == True).count()

        assert total_cards == 5  # 2 actives + 3 archivées
        assert active_cards_count == 2
        assert archived_cards_count == 3
        assert cards_count == active_cards_count  # La fonction doit retourner le même nombre que le comptage manuel

    def test_create_list_success(self, db_session):
        """Test de création d'une liste avec succès."""
        # Arrange
        list_data = KanbanListCreate(name="Nouvelle Liste", order=1)
        
        # Act
        result = KanbanListService.create_list(db_session, list_data)
        
        # Assert
        assert result is not None
        assert result.name == "Nouvelle Liste"
        assert result.order == 1
        assert result.id is not None

    def test_create_list_duplicate_name(self, db_session, sample_lists):
        """Test de création d'une liste avec un nom déjà existant."""
        # Arrange
        list_data = KanbanListCreate(name="A faire", order=4)  # Nom déjà existant
        
        # Act & Assert
        with pytest.raises(ValueError, match="Une liste avec le nom 'A faire' existe déjà"):
            KanbanListService.create_list(db_session, list_data)

    def test_create_list_duplicate_name_case_insensitive(self, db_session, sample_lists):
        """Test de création d'une liste avec un nom déjà existant (insensible à la casse)."""
        # Arrange
        list_data = KanbanListCreate(name="a FAIRE", order=4)  # Même nom, casse différente
        
        # Act & Assert
        with pytest.raises(ValueError, match="Une liste avec le nom 'a FAIRE' existe déjà"):
            KanbanListService.create_list(db_session, list_data)

    def test_create_list_invalid_order(self, db_session):
        """Test de création d'une liste avec un ordre invalide."""
        # Test ordre négatif - Pydantic validation should catch this
        with pytest.raises(Exception):  # ValidationError from Pydantic
            list_data = KanbanListCreate(name="Test List", order=0)
        
        # Test ordre trop grand - Pydantic validation should catch this
        with pytest.raises(Exception):  # ValidationError from Pydantic
            list_data = KanbanListCreate(name="Test List", order=10000)

    def test_create_list_max_lists_limit(self, db_session):
        """Test de la limite maximale de listes."""
        # Arrange - Créer 50 listes (limite)
        for i in range(50):
            list_data = KanbanListCreate(name=f"List {i+1}", order=i+1)
            KanbanListService.create_list(db_session, list_data)
        
        # Act & Assert - Tenter de créer une 51ème liste
        list_data = KanbanListCreate(name="List 51", order=51)
        with pytest.raises(ValueError, match="Nombre maximum de listes atteint"):
            KanbanListService.create_list(db_session, list_data)

    def test_create_list_duplicate_order_shifts_others(self, db_session, sample_lists):
        """Test que créer une liste avec un ordre existant décale les autres."""
        # Arrange
        list_data = KanbanListCreate(name="Nouvelle Liste", order=2)  # Ordre déjà pris
        
        # Act
        result = KanbanListService.create_list(db_session, list_data)
        
        # Assert
        assert result.order == 2
        
        # Vérifier que les autres listes ont été décalées
        all_lists = KanbanListService.get_lists(db_session)
        assert len(all_lists) == 4
        
        # L'ancienne liste "En cours" devrait maintenant être à l'ordre 3
        # L'ancienne liste "Terminé" devrait maintenant être à l'ordre 4
        orders = [lst.order for lst in all_lists]
        assert orders == [1, 2, 3, 4]

    def test_update_list_success(self, db_session, sample_lists):
        """Test de mise à jour d'une liste avec succès."""
        # Arrange
        list_id = sample_lists[0].id
        update_data = KanbanListUpdate(name="Nouveau Nom", order=1)

        # Act
        result = KanbanListService.update_list(db_session, list_id, update_data)

        # Assert
        assert result is not None
        assert result.name == "Nouveau Nom"
        assert result.order == 1  # Ordre inchangé

    def test_update_list_non_existing(self, db_session):
        """Test de mise à jour d'une liste inexistante."""
        # Arrange
        update_data = KanbanListUpdate(name="Nouveau Nom", order=1)

        # Act
        result = KanbanListService.update_list(db_session, 999, update_data)
        
        # Assert
        assert result is None

    def test_update_list_no_data(self, db_session, sample_lists):
        """Test de mise à jour sans données."""
        # Arrange
        list_id = sample_lists[0].id
        update_data = KanbanListUpdate(name=None, order=None)  # Aucune donnée

        # Act & Assert
        with pytest.raises(ValueError, match="Aucune donnée fournie pour la mise à jour"):
            KanbanListService.update_list(db_session, list_id, update_data)

    def test_update_list_duplicate_name(self, db_session, sample_lists):
        """Test de mise à jour avec un nom déjà existant."""
        # Arrange
        list_id = sample_lists[0].id
        update_data = KanbanListUpdate(name="En cours", order=1)  # Nom de la 2ème liste

        # Act & Assert
        with pytest.raises(ValueError, match="Une liste avec le nom 'En cours' existe déjà"):
            KanbanListService.update_list(db_session, list_id, update_data)

    def test_update_list_order_change(self, db_session, sample_lists):
        """Test de changement d'ordre lors de la mise à jour."""
        # Arrange
        list_id = sample_lists[0].id  # "A faire" (ordre 1)
        update_data = KanbanListUpdate(name=None, order=3)  # Déplacer à la fin

        # Act
        result = KanbanListService.update_list(db_session, list_id, update_data)

        # Assert
        assert result is not None
        assert result.order == 3
        
        # Vérifier que les autres listes ont été réorganisées
        all_lists = KanbanListService.get_lists(db_session)
        names_by_order = [lst.name for lst in all_lists]
        assert names_by_order == ["En cours", "Terminé", "A faire"]

    def test_delete_list_success(self, db_session, sample_lists):
        """Test de suppression d'une liste avec succès."""
        # Arrange
        list_to_delete_id = sample_lists[1].id  # "En cours"
        target_list_id = sample_lists[0].id     # "A faire"
        
        # Act
        result = KanbanListService.delete_list(db_session, list_to_delete_id, target_list_id)
        
        # Assert
        assert result is True
        
        # Vérifier que la liste a été supprimée
        remaining_lists = KanbanListService.get_lists(db_session)
        assert len(remaining_lists) == 2
        assert all(lst.id != list_to_delete_id for lst in remaining_lists)

    def test_delete_list_last_list(self, db_session):
        """Test de suppression de la dernière liste (doit échouer)."""
        # Arrange - Créer une seule liste
        single_list = KanbanList(name="Seule Liste", order=1)
        db_session.add(single_list)
        db_session.commit()
        db_session.refresh(single_list)
        
        # Act & Assert
        with pytest.raises(ValueError, match="Impossible de supprimer la dernière liste"):
            KanbanListService.delete_list(db_session, single_list.id, single_list.id)

    def test_delete_list_non_existing(self, db_session, sample_lists):
        """Test de suppression d'une liste inexistante."""
        # Act & Assert
        with pytest.raises(ValueError, match="La liste avec l'ID 999 n'existe pas"):
            KanbanListService.delete_list(db_session, 999, sample_lists[0].id)

    def test_delete_list_invalid_target(self, db_session, sample_lists):
        """Test de suppression avec une liste de destination inexistante."""
        # Act & Assert
        with pytest.raises(ValueError, match="La liste de destination avec l'ID 999 n'existe pas"):
            KanbanListService.delete_list(db_session, sample_lists[0].id, 999)

    def test_delete_list_same_as_target(self, db_session, sample_lists):
        """Test de suppression avec la même liste comme destination."""
        # Arrange
        list_id = sample_lists[0].id
        
        # Act & Assert
        with pytest.raises(ValueError, match="La liste de destination ne peut pas être la même"):
            KanbanListService.delete_list(db_session, list_id, list_id)

    def test_delete_list_with_cards(self, db_session, sample_lists):
        """Test de suppression d'une liste contenant des cartes."""
        # Arrange
        list_to_delete_id = sample_lists[1].id  # "En cours"
        target_list_id = sample_lists[0].id     # "A faire"
        
        # Créer des cartes dans la liste à supprimer
        cards = [
            Card(titre="Card 1", description="Desc 1", list_id=list_to_delete_id, created_by=1, assignee_id=1),
            Card(titre="Card 2", description="Desc 2", list_id=list_to_delete_id, created_by=1, assignee_id=1)
        ]
        
        for card in cards:
            db_session.add(card)
        db_session.commit()
        
        # Act
        result = KanbanListService.delete_list(db_session, list_to_delete_id, target_list_id)
        
        # Assert
        assert result is True
        
        # Vérifier que les cartes ont été déplacées
        moved_cards = db_session.query(Card).filter(Card.list_id == target_list_id).all()
        assert len(moved_cards) == 2

    def test_delete_list_invalid_ids(self, db_session):
        """Test de suppression avec des IDs invalides."""
        # Test ID négatif pour la liste à supprimer
        with pytest.raises(ValueError, match="L'ID de la liste à supprimer doit être un entier positif"):
            KanbanListService.delete_list(db_session, -1, 1)
        
        # Test ID négatif pour la liste de destination
        with pytest.raises(ValueError, match="L'ID de la liste de destination doit être un entier positif"):
            KanbanListService.delete_list(db_session, 1, -1)

    def test_reorder_lists_success(self, db_session, sample_lists):
        """Test de réorganisation des listes avec succès."""
        # Arrange
        list_orders = {
            sample_lists[0].id: 3,  # "A faire" -> ordre 3
            sample_lists[1].id: 1,  # "En cours" -> ordre 1
            sample_lists[2].id: 2   # "Terminé" -> ordre 2
        }
        
        # Act
        result = KanbanListService.reorder_lists(db_session, list_orders)
        
        # Assert
        assert result is True
        
        # Vérifier le nouvel ordre
        reordered_lists = KanbanListService.get_lists(db_session)
        names_by_order = [lst.name for lst in reordered_lists]
        assert names_by_order == ["En cours", "Terminé", "A faire"]

    def test_reorder_lists_non_existing_list(self, db_session, sample_lists):
        """Test de réorganisation avec une liste inexistante."""
        # Arrange
        list_orders = {
            sample_lists[0].id: 1,
            999: 2  # Liste inexistante
        }
        
        # Act & Assert
        with pytest.raises(ValueError, match=r"Les listes suivantes n'existent pas: \{999\}"):
            KanbanListService.reorder_lists(db_session, list_orders)

    def test_reorder_lists_negative_order(self, db_session, sample_lists):
        """Test de réorganisation avec un ordre négatif."""
        # Arrange
        list_orders = {
            sample_lists[0].id: -1,  # Ordre négatif
            sample_lists[1].id: 1
        }
        
        # Act & Assert
        with pytest.raises(ValueError, match="Tous les ordres doivent être positifs"):
            KanbanListService.reorder_lists(db_session, list_orders)

    def test_reorder_lists_duplicate_orders(self, db_session, sample_lists):
        """Test de réorganisation avec des ordres dupliqués."""
        # Arrange
        list_orders = {
            sample_lists[0].id: 1,
            sample_lists[1].id: 1,  # Ordre dupliqué
            sample_lists[2].id: 2
        }
        
        # Act & Assert
        with pytest.raises(ValueError, match="Les ordres doivent être uniques"):
            KanbanListService.reorder_lists(db_session, list_orders)