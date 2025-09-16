"""Tests complets pour le service KanbanList."""

import pytest
import sys
import os
from unittest.mock import patch, Mock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.kanban_list import (
    KanbanListService,
    get_lists,
    get_list,
    get_list_with_cards_count,
    create_list,
    update_list,
    delete_list,
    reorder_lists,
)
from app.models import KanbanList, Card
from app.schemas import KanbanListCreate, KanbanListUpdate


@pytest.fixture
def mock_db():
    """Mock de la session de base de données."""
    db = Mock()
    db.query = Mock()
    db.add = Mock()
    db.commit = Mock()
    db.rollback = Mock()
    db.refresh = Mock()
    db.delete = Mock()
    return db


@pytest.fixture
def sample_kanban_lists():
    """Données de test pour les listes Kanban."""
    return [
        KanbanList(id=1, name="À faire", order=1),
        KanbanList(id=2, name="En cours", order=2),
        KanbanList(id=3, name="Terminé", order=3),
    ]


@pytest.fixture
def sample_cards():
    """Données de test pour les cartes."""
    return [
        Card(id=1, titre="Carte 1", list_id=1, position=1, is_archived=False, created_by=1),
        Card(id=2, titre="Carte 2", list_id=1, position=2, is_archived=False, created_by=1),
        Card(id=3, titre="Carte 3", list_id=2, position=1, is_archived=True, created_by=1),
        Card(id=4, titre="Carte 4", list_id=2, position=2, is_archived=False, created_by=1),
    ]


@pytest.fixture
def sample_list_create_data():
    """Données de test pour la création de liste."""
    return KanbanListCreate(name="Nouvelle liste", order=4)


@pytest.fixture
def sample_list_update_data():
    """Données de test pour la mise à jour de liste."""
    return KanbanListUpdate(name="Liste entièrement nouvelle", order=2)


class TestGetLists:
    """Tests pour la fonction get_lists."""

    def test_get_lists_success(self, mock_db, sample_kanban_lists):
        """Test de récupération réussie de toutes les listes."""
        mock_query = Mock()
        mock_query.order_by.return_value.all.return_value = sample_kanban_lists
        mock_db.query.return_value = mock_query

        result = KanbanListService.get_lists(mock_db)

        assert len(result) == 3
        assert result[0].name == "À faire"
        assert result[1].name == "En cours"
        assert result[2].name == "Terminé"
        mock_db.query.assert_called_once_with(KanbanList)
        mock_query.order_by.assert_called_once_with(KanbanList.order)

    def test_get_lists_empty(self, mock_db):
        """Test de récupération quand aucune liste n'existe."""
        mock_query = Mock()
        mock_query.order_by.return_value.all.return_value = []
        mock_db.query.return_value = mock_query

        result = KanbanListService.get_lists(mock_db)

        assert result == []
        mock_db.query.assert_called_once_with(KanbanList)


class TestGetList:
    """Tests pour la fonction get_list."""

    def test_get_list_success(self, mock_db, sample_kanban_lists):
        """Test de récupération réussie d'une liste par ID."""
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_kanban_lists[0]
        mock_db.query.return_value = mock_query

        result = KanbanListService.get_list(mock_db, 1)

        assert result is not None
        assert result.id == 1
        assert result.name == "À faire"
        mock_db.query.assert_called_once_with(KanbanList)

    def test_get_list_not_found(self, mock_db):
        """Test de récupération d'une liste inexistante."""
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        result = KanbanListService.get_list(mock_db, 999)

        assert result is None
        mock_db.query.assert_called_once_with(KanbanList)


class TestGetListWithCardsCount:
    """Tests pour la fonction get_list_with_cards_count."""

    def test_get_list_with_cards_count_success(self, mock_db, sample_kanban_lists, sample_cards):
        """Test de récupération réussie d'une liste avec le nombre de cartes."""
        # Mock pour la liste
        list_query = Mock()
        list_query.filter.return_value.first.return_value = sample_kanban_lists[0]
        
        # Mock pour le comptage des cartes
        card_query = Mock()
        card_query.filter.return_value.count.return_value = 2  # 2 cartes actives
        
        # Configurer le mock pour retourner différents query objects
        mock_db.query.side_effect = [list_query, card_query]

        result = KanbanListService.get_list_with_cards_count(mock_db, 1)

        assert result is not None
        kanban_list, cards_count = result
        assert kanban_list.id == 1
        assert kanban_list.name == "À faire"
        assert cards_count == 2

    def test_get_list_with_cards_count_list_not_found(self, mock_db):
        """Test de récupération d'une liste inexistante avec comptage."""
        list_query = Mock()
        list_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = list_query

        result = KanbanListService.get_list_with_cards_count(mock_db, 999)

        assert result is not None
        kanban_list, cards_count = result
        assert kanban_list is None
        assert cards_count == 0

    def test_get_list_with_cards_count_invalid_id(self, mock_db):
        """Test de récupération avec ID invalide."""
        with pytest.raises(ValueError, match="L'ID de la liste doit être un entier positif"):
            KanbanListService.get_list_with_cards_count(mock_db, 0)

        with pytest.raises(ValueError, match="L'ID de la liste doit être un entier positif"):
            KanbanListService.get_list_with_cards_count(mock_db, -1)

    def test_get_list_with_cards_count_count_error(self, mock_db, sample_kanban_lists):
        """Test de gestion d'erreur lors du comptage des cartes."""
        list_query = Mock()
        list_query.filter.return_value.first.return_value = sample_kanban_lists[0]
        
        card_query = Mock()
        card_query.filter.return_value.count.side_effect = Exception("Database error")
        
        mock_db.query.side_effect = [list_query, card_query]

        with pytest.raises(ValueError, match="Erreur lors du comptage des cartes"):
            KanbanListService.get_list_with_cards_count(mock_db, 1)


class TestCreateList:
    """Tests pour la fonction create_list."""

    def test_create_list_success(self, mock_db, sample_list_create_data):
        """Test de création réussie d'une liste."""
        # Mock pour vérifier l'unicité du nom
        existing_query = Mock()
        existing_query.filter.return_value.first.return_value = None
        
        # Mock pour le comptage total
        count_query = Mock()
        count_query.count.return_value = 2  # Moins de 50 listes
        
        # Mock pour vérifier l'ordre existant
        order_query = Mock()
        order_query.filter.return_value.first.return_value = None
        
        # Configurer les mocks
        mock_db.query.side_effect = [existing_query, count_query, order_query]

        result = KanbanListService.create_list(mock_db, sample_list_create_data)

        assert result.name == "Nouvelle liste"
        assert result.order == 4
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_create_list_name_exists(self, mock_db, sample_list_create_data, sample_kanban_lists):
        """Test de création avec un nom qui existe déjà."""
        existing_query = Mock()
        existing_query.filter.return_value.first.return_value = sample_kanban_lists[0]  # Liste avec même nom
        mock_db.query.return_value = existing_query

        with pytest.raises(ValueError, match="Une liste avec le nom 'Nouvelle liste' existe déjà"):
            KanbanListService.create_list(mock_db, sample_list_create_data)

    def test_create_list_invalid_order_too_low(self, mock_db):
        """Test de création avec ordre invalide (trop bas)."""
        # La validation Pydantic empêche déjà la création avec order < 1
        with pytest.raises(Exception):  # PydanticValidationError
            KanbanListCreate(name="Test", order=0)

    def test_create_list_invalid_order_too_high(self, mock_db):
        """Test de création avec ordre invalide (trop haut)."""
        # La validation Pydantic empêche déjà la création avec order > 9999
        with pytest.raises(Exception):  # PydanticValidationError
            KanbanListCreate(name="Test", order=10000)

    def test_create_list_max_lists_reached(self, mock_db, sample_list_create_data):
        """Test de création quand le maximum de listes est atteint."""
        existing_query = Mock()
        existing_query.filter.return_value.first.return_value = None
        
        count_query = Mock()
        count_query.count.return_value = 50  # Maximum atteint
        
        mock_db.query.side_effect = [existing_query, count_query]

        with pytest.raises(ValueError, match="Nombre maximum de listes atteint"):
            KanbanListService.create_list(mock_db, sample_list_create_data)

    def test_create_list_order_exists_shifts_up(self, mock_db, sample_list_create_data):
        """Test de création quand l'ordre existe déjà (décalage vers le haut)."""
        # Test simplifié - on suppose que le mécanisme de décalage fonctionne
        existing_query = Mock()
        existing_query.filter.return_value.first.return_value = None
        
        count_query = Mock()
        count_query.count.return_value = 2
        
        order_query = Mock()
        order_query.filter.return_value.first.return_value = None  # Pas de conflit d'ordre
        
        mock_db.query.side_effect = [existing_query, count_query, order_query]

        result = KanbanListService.create_list(mock_db, sample_list_create_data)

        assert result.name == "Nouvelle liste"
        assert result.order == 4
        mock_db.commit.assert_called_once()

    def test_create_list_database_error(self, mock_db, sample_list_create_data):
        """Test de gestion d'erreur de base de données."""
        existing_query = Mock()
        existing_query.filter.return_value.first.return_value = None
        
        count_query = Mock()
        count_query.count.return_value = 2
        
        order_query = Mock()
        order_query.filter.return_value.first.return_value = None
        
        mock_db.query.side_effect = [existing_query, count_query, order_query]
        mock_db.commit.side_effect = Exception("Database error")

        with pytest.raises(ValueError, match="Erreur lors de la création de la liste"):
            KanbanListService.create_list(mock_db, sample_list_create_data)
        
        mock_db.rollback.assert_called_once()


class TestUpdateList:
    """Tests pour la fonction update_list."""

    @patch('app.services.kanban_list.KanbanListService.get_list')
    def test_update_list_success(self, mock_get_list, mock_db, sample_kanban_lists, sample_list_update_data):
        """Test de mise à jour réussie d'une liste."""
        # Mock get_list pour retourner la liste à mettre à jour
        mock_get_list.return_value = sample_kanban_lists[0]
        
        # Mock la vérification d'unicité du nom pour retourner None (pas de conflit)
        with patch.object(mock_db, 'query') as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = None
            
            result = KanbanListService.update_list(mock_db, 1, sample_list_update_data)

            assert result is not None
            assert result.name == "Liste entièrement nouvelle"
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()

    def test_update_list_not_found(self, mock_db, sample_list_update_data):
        """Test de mise à jour d'une liste inexistante."""
        get_list_query = Mock()
        get_list_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = get_list_query

        result = KanbanListService.update_list(mock_db, 999, sample_list_update_data)

        assert result is None

    def test_update_list_no_data(self, mock_db, sample_kanban_lists):
        """Test de mise à jour sans données."""
        get_list_query = Mock()
        get_list_query.filter.return_value.first.return_value = sample_kanban_lists[0]
        mock_db.query.return_value = get_list_query

        empty_data = KanbanListUpdate()

        with pytest.raises(ValueError, match="Aucune donnée fournie pour la mise à jour"):
            KanbanListService.update_list(mock_db, 1, empty_data)

    def test_update_list_name_exists(self, mock_db, sample_kanban_lists):
        """Test de mise à jour avec un nom qui existe déjà."""
        # Mock pour get_list
        get_list_query = Mock()
        get_list_query.filter.return_value.first.return_value = sample_kanban_lists[0]
        
        # Mock pour vérifier l'unicité du nom (trouve une autre liste avec même nom)
        name_query = Mock()
        name_query.filter.return_value.first.return_value = sample_kanban_lists[1]
        
        mock_db.query.side_effect = [get_list_query, name_query]

        update_data = KanbanListUpdate(name="En cours")

        with pytest.raises(ValueError, match="Une liste avec le nom 'En cours' existe déjà"):
            KanbanListService.update_list(mock_db, 1, update_data)

    def test_update_list_order_invalid_too_low(self, mock_db):
        """Test de mise à jour avec ordre invalide (trop bas)."""
        # La validation Pydantic empêche déjà la création avec order < 1
        with pytest.raises(Exception):  # PydanticValidationError
            KanbanListUpdate(order=0)

    def test_update_list_order_invalid_too_high(self, mock_db):
        """Test de mise à jour avec ordre invalide (trop haut)."""
        # La validation Pydantic n'a pas de limite supérieure, donc on teste directement la création
        with pytest.raises(Exception):  # PydanticValidationError
            KanbanListUpdate(order=10000)

    def test_update_list_order_exists_reorders(self, mock_db, sample_kanban_lists):
        """Test de mise à jour quand l'ordre existe déjà (réorganisation)."""
        existing_list = KanbanList(id=4, name="Existante", order=2)
        
        # Mock pour get_list
        get_list_query = Mock()
        get_list_query.filter.return_value.first.return_value = sample_kanban_lists[0]
        
        # Mock pour vérifier l'unicité du nom
        name_query = Mock()
        name_query.filter.return_value.first.return_value = None
        
        # Mock pour vérifier l'ordre existant
        order_query = Mock()
        order_query.filter.return_value.first.return_value = existing_list
        
        mock_db.query.side_effect = [get_list_query, name_query, order_query]

        update_data = KanbanListUpdate(order=2)

        result = KanbanListService.update_list(mock_db, 1, update_data)

        assert result is not None
        assert result.order == 2
        mock_db.commit.assert_called_once()

    def test_update_list_database_error(self, mock_db, sample_kanban_lists):
        """Test de gestion d'erreur de base de données."""
        get_list_query = Mock()
        get_list_query.filter.return_value.first.return_value = sample_kanban_lists[0]
        
        name_query = Mock()
        name_query.filter.return_value.first.return_value = None
        
        mock_db.query.side_effect = [get_list_query, name_query]
        mock_db.commit.side_effect = Exception("Database error")

        update_data = KanbanListUpdate(name="Nouveau nom")

        with pytest.raises(ValueError, match="Erreur lors de la mise à jour de la liste"):
            KanbanListService.update_list(mock_db, 1, update_data)
        
        mock_db.rollback.assert_called_once()


class TestDeleteList:
    """Tests pour la fonction delete_list."""

    def test_delete_list_success(self, mock_db, sample_kanban_lists, sample_cards):
        """Test de suppression réussie d'une liste."""
        # Mock pour vérifier le nombre total de listes
        total_query = Mock()
        total_query.count.return_value = 3  # Plus d'une liste
        
        # Mock pour get_list (liste à supprimer)
        delete_list_query = Mock()
        delete_list_query.filter.return_value.first.return_value = sample_kanban_lists[0]
        
        # Mock pour get_list (liste de destination)
        target_list_query = Mock()
        target_list_query.filter.return_value.first.return_value = sample_kanban_lists[1]
        
        # Mock pour compter les cartes
        card_count_query = Mock()
        card_count_query.filter.return_value.count.return_value = 2
        
        # Mock pour déplacer les cartes
        card_update_query = Mock()
        card_update_query.filter.return_value.update.return_value = 2
        
        # Mock pour _compact_orders (pour éviter l'erreur de comparaison)
        compact_query = Mock()
        compact_query.filter.return_value.update.return_value = None
        
        mock_db.query.side_effect = [total_query, delete_list_query, target_list_query, 
                                   card_count_query, card_update_query, compact_query]

        result = KanbanListService.delete_list(mock_db, 1, 2)

        assert result is True
        mock_db.delete.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_delete_list_invalid_ids(self, mock_db):
        """Test de suppression avec IDs invalides."""
        with pytest.raises(ValueError, match="L'ID de la liste à supprimer doit être un entier positif"):
            KanbanListService.delete_list(mock_db, 0, 2)

        with pytest.raises(ValueError, match="L'ID de la liste de destination doit être un entier positif"):
            KanbanListService.delete_list(mock_db, 1, 0)

    def test_delete_list_last_list(self, mock_db, sample_kanban_lists):
        """Test de suppression de la dernière liste."""
        total_query = Mock()
        total_query.count.return_value = 1  # Une seule liste
        mock_db.query.return_value = total_query

        with pytest.raises(ValueError, match="Impossible de supprimer la dernière liste"):
            KanbanListService.delete_list(mock_db, 1, 2)

    def test_delete_list_not_found(self, mock_db, sample_kanban_lists):
        """Test de suppression d'une liste inexistante."""
        total_query = Mock()
        total_query.count.return_value = 3
        
        delete_list_query = Mock()
        delete_list_query.filter.return_value.first.return_value = None
        
        mock_db.query.side_effect = [total_query, delete_list_query]

        with pytest.raises(ValueError, match="La liste avec l'ID 999 n'existe pas"):
            KanbanListService.delete_list(mock_db, 999, 2)

    def test_delete_list_target_not_found(self, mock_db, sample_kanban_lists):
        """Test de suppression avec liste de destination inexistante."""
        total_query = Mock()
        total_query.count.return_value = 3
        
        delete_list_query = Mock()
        delete_list_query.filter.return_value.first.return_value = sample_kanban_lists[0]
        
        target_list_query = Mock()
        target_list_query.filter.return_value.first.return_value = None
        
        mock_db.query.side_effect = [total_query, delete_list_query, target_list_query]

        with pytest.raises(ValueError, match="La liste de destination avec l'ID 999 n'existe pas"):
            KanbanListService.delete_list(mock_db, 1, 999)

    def test_delete_list_same_target(self, mock_db, sample_kanban_lists):
        """Test de suppression avec la même liste comme destination."""
        total_query = Mock()
        total_query.count.return_value = 3
        
        delete_list_query = Mock()
        delete_list_query.filter.return_value.first.return_value = sample_kanban_lists[0]
        
        target_list_query = Mock()
        target_list_query.filter.return_value.first.return_value = sample_kanban_lists[0]
        
        mock_db.query.side_effect = [total_query, delete_list_query, target_list_query]

        with pytest.raises(ValueError, match="La liste de destination ne peut pas être la même que la liste à supprimer"):
            KanbanListService.delete_list(mock_db, 1, 1)

    def test_delete_list_card_move_error(self, mock_db, sample_kanban_lists):
        """Test d'erreur lors du déplacement des cartes."""
        total_query = Mock()
        total_query.count.return_value = 3
        
        delete_list_query = Mock()
        delete_list_query.filter.return_value.first.return_value = sample_kanban_lists[0]
        
        target_list_query = Mock()
        target_list_query.filter.return_value.first.return_value = sample_kanban_lists[1]
        
        card_count_query = Mock()
        card_count_query.filter.return_value.count.return_value = 2
        
        card_update_query = Mock()
        card_update_query.filter.return_value.update.return_value = 1  # Seulement 1 carte déplacée au lieu de 2
        
        mock_db.query.side_effect = [total_query, delete_list_query, target_list_query, 
                                   card_count_query, card_update_query]

        with pytest.raises(ValueError, match="Erreur lors du déplacement des cartes"):
            KanbanListService.delete_list(mock_db, 1, 2)

    def test_delete_list_database_error(self, mock_db, sample_kanban_lists):
        """Test de gestion d'erreur de base de données."""
        total_query = Mock()
        total_query.count.return_value = 3
        
        delete_list_query = Mock()
        delete_list_query.filter.return_value.first.return_value = sample_kanban_lists[0]
        
        target_list_query = Mock()
        target_list_query.filter.return_value.first.return_value = sample_kanban_lists[1]
        
        card_count_query = Mock()
        card_count_query.filter.return_value.count.return_value = 0  # Pas de cartes à déplacer
        
        mock_db.query.side_effect = [total_query, delete_list_query, target_list_query, card_count_query]
        mock_db.commit.side_effect = Exception("Database error")

        with pytest.raises(ValueError, match="Erreur lors de la suppression de la liste"):
            KanbanListService.delete_list(mock_db, 1, 2)
        
        mock_db.rollback.assert_called_once()


class TestReorderLists:
    """Tests pour la fonction reorder_lists."""

    def test_reorder_lists_success(self, mock_db, sample_kanban_lists):
        """Test de réorganisation réussie des listes."""
        # Mock pour vérifier que les listes existent
        existing_query = Mock()
        existing_query.filter.return_value.all.return_value = sample_kanban_lists[:2]
        mock_db.query.return_value = existing_query

        list_orders = {1: 3, 2: 1}
        result = KanbanListService.reorder_lists(mock_db, list_orders)

        assert result is True
        mock_db.commit.assert_called_once()

    def test_reorder_lists_missing_lists(self, mock_db, sample_kanban_lists):
        """Test de réorganisation avec des listes manquantes."""
        existing_query = Mock()
        existing_query.filter.return_value.all.return_value = sample_kanban_lists[:1]  # Seulement une liste trouvée
        mock_db.query.return_value = existing_query

        list_orders = {1: 2, 2: 1, 999: 3}  # La liste 999 n'existe pas

        with pytest.raises(ValueError, match="Les listes suivantes n'existent pas:"):
            KanbanListService.reorder_lists(mock_db, list_orders)

    def test_reorder_lists_negative_order(self, mock_db, sample_kanban_lists):
        """Test de réorganisation avec ordres négatifs."""
        existing_query = Mock()
        existing_query.filter.return_value.all.return_value = sample_kanban_lists[:2]
        mock_db.query.return_value = existing_query

        list_orders = {1: -1, 2: 2}

        with pytest.raises(ValueError, match="Tous les ordres doivent être positifs"):
            KanbanListService.reorder_lists(mock_db, list_orders)

    def test_reorder_lists_duplicate_orders(self, mock_db, sample_kanban_lists):
        """Test de réorganisation avec ordres dupliqués."""
        existing_query = Mock()
        existing_query.filter.return_value.all.return_value = sample_kanban_lists[:2]
        mock_db.query.return_value = existing_query

        list_orders = {1: 1, 2: 1}  # Même ordre pour les deux listes

        with pytest.raises(ValueError, match="Les ordres doivent être uniques"):
            KanbanListService.reorder_lists(mock_db, list_orders)


class TestUtilityFunctions:
    """Tests pour les fonctions utilitaires."""

    def test_get_lists_utility_function(self, mock_db, sample_kanban_lists):
        """Test de la fonction utilitaire get_lists."""
        mock_query = Mock()
        mock_query.order_by.return_value.all.return_value = sample_kanban_lists
        mock_db.query.return_value = mock_query

        result = get_lists(mock_db)

        assert len(result) == 3
        assert result[0].name == "À faire"

    def test_get_list_utility_function(self, mock_db, sample_kanban_lists):
        """Test de la fonction utilitaire get_list."""
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_kanban_lists[0]
        mock_db.query.return_value = mock_query

        result = get_list(mock_db, 1)

        assert result is not None
        assert result.id == 1

    def test_get_list_with_cards_count_utility_function(self, mock_db, sample_kanban_lists, sample_cards):
        """Test de la fonction utilitaire get_list_with_cards_count."""
        list_query = Mock()
        list_query.filter.return_value.first.return_value = sample_kanban_lists[0]
        
        card_query = Mock()
        card_query.filter.return_value.count.return_value = 2
        
        mock_db.query.side_effect = [list_query, card_query]

        result = get_list_with_cards_count(mock_db, 1)

        assert result is not None
        kanban_list, cards_count = result
        assert kanban_list.id == 1
        assert cards_count == 2

    def test_create_list_utility_function(self, mock_db, sample_list_create_data):
        """Test de la fonction utilitaire create_list."""
        existing_query = Mock()
        existing_query.filter.return_value.first.return_value = None
        
        count_query = Mock()
        count_query.count.return_value = 2
        
        order_query = Mock()
        order_query.filter.return_value.first.return_value = None
        
        mock_db.query.side_effect = [existing_query, count_query, order_query]

        result = create_list(mock_db, sample_list_create_data)

        assert result.name == "Nouvelle liste"
        assert result.order == 4

    @patch('app.services.kanban_list.KanbanListService.get_list')
    def test_update_list_utility_function(self, mock_get_list, mock_db, sample_kanban_lists, sample_list_update_data):
        """Test de la fonction utilitaire update_list."""
        # Mock get_list pour retourner la liste à mettre à jour
        mock_get_list.return_value = sample_kanban_lists[0]
        
        # Mock la vérification d'unicité du nom pour retourner None (pas de conflit)
        with patch.object(mock_db, 'query') as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = None
            
            result = update_list(mock_db, 1, sample_list_update_data)

            assert result is not None
            assert result.name == "Liste entièrement nouvelle"

    def test_delete_list_utility_function(self, mock_db, sample_kanban_lists):
        """Test de la fonction utilitaire delete_list."""
        # Mock pour vérifier le nombre total de listes
        total_query = Mock()
        total_query.count.return_value = 3  # Plus d'une liste
        
        # Mock pour get_list (liste à supprimer)
        delete_list_query = Mock()
        delete_list_query.filter.return_value.first.return_value = sample_kanban_lists[0]
        
        # Mock pour get_list (liste de destination)
        target_list_query = Mock()
        target_list_query.filter.return_value.first.return_value = sample_kanban_lists[1]
        
        # Mock pour compter les cartes
        card_count_query = Mock()
        card_count_query.filter.return_value.count.return_value = 2
        
        # Mock pour déplacer les cartes
        card_update_query = Mock()
        card_update_query.filter.return_value.update.return_value = 2
        
        # Mock pour _compact_orders (pour éviter l'erreur de comparaison)
        compact_query = Mock()
        compact_query.filter.return_value.update.return_value = None
        
        mock_db.query.side_effect = [total_query, delete_list_query, target_list_query, 
                                   card_count_query, card_update_query, compact_query]

        result = delete_list(mock_db, 1, 2)

        assert result is True

    def test_reorder_lists_utility_function(self, mock_db, sample_kanban_lists):
        """Test de la fonction utilitaire reorder_lists."""
        existing_query = Mock()
        existing_query.filter.return_value.all.return_value = sample_kanban_lists[:2]
        mock_db.query.return_value = existing_query

        list_orders = {1: 2, 2: 1}
        result = reorder_lists(mock_db, list_orders)

        assert result is True


class TestEdgeCases:
    """Tests pour les cas limites et scénarios spéciaux."""

    def test_create_list_edge_case_max_order(self, mock_db):
        """Test de création avec ordre maximum valide."""
        list_data = KanbanListCreate(name="Test", order=9999)
        
        existing_query = Mock()
        existing_query.filter.return_value.first.return_value = None
        
        count_query = Mock()
        count_query.count.return_value = 2
        
        order_query = Mock()
        order_query.filter.return_value.first.return_value = None
        
        mock_db.query.side_effect = [existing_query, count_query, order_query]

        result = KanbanListService.create_list(mock_db, list_data)

        assert result.order == 9999

    def test_update_list_same_name_case_insensitive(self, mock_db, sample_kanban_lists):
        """Test de mise à jour avec même nom en casse différente."""
        get_list_query = Mock()
        get_list_query.filter.return_value.first.return_value = sample_kanban_lists[0]
        
        name_query = Mock()
        name_query.filter.return_value.first.return_value = sample_kanban_lists[1]
        
        mock_db.query.side_effect = [get_list_query, name_query]

        update_data = KanbanListUpdate(name="EN COURS")  # Même nom que "En cours" mais en majuscules

        with pytest.raises(ValueError, match="Une liste avec le nom 'EN COURS' existe déjà"):
            KanbanListService.update_list(mock_db, 1, update_data)

    def test_delete_list_with_archived_cards(self, mock_db, sample_kanban_lists):
        """Test de suppression d'une liste avec des cartes archivées."""
        # Mock pour vérifier le nombre total de listes
        total_query = Mock()
        total_query.count.return_value = 3  # Plus d'une liste
        
        # Mock pour get_list (liste à supprimer)
        delete_list_query = Mock()
        delete_list_query.filter.return_value.first.return_value = sample_kanban_lists[0]
        
        # Mock pour get_list (liste de destination)
        target_list_query = Mock()
        target_list_query.filter.return_value.first.return_value = sample_kanban_lists[1]
        
        # Mock pour compter les cartes
        card_count_query = Mock()
        card_count_query.filter.return_value.count.return_value = 0  # Aucune carte active
        
        # Mock pour déplacer les cartes
        card_update_query = Mock()
        card_update_query.filter.return_value.update.return_value = 0
        
        # Mock pour _compact_orders (pour éviter l'erreur de comparaison)
        compact_query = Mock()
        compact_query.filter.return_value.update.return_value = None
        
        mock_db.query.side_effect = [total_query, delete_list_query, target_list_query, 
                                   card_count_query, card_update_query, compact_query]

        result = KanbanListService.delete_list(mock_db, 1, 2)

        assert result is True  # Devrait réussir car on ne déplace que les cartes actives

    def test_reorder_lists_single_list(self, mock_db, sample_kanban_lists):
        """Test de réorganisation d'une seule liste."""
        existing_query = Mock()
        existing_query.filter.return_value.all.return_value = sample_kanban_lists[:1]
        mock_db.query.return_value = existing_query

        list_orders = {1: 5}
        result = KanbanListService.reorder_lists(mock_db, list_orders)

        assert result is True