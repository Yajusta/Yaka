"""Tests complets pour le modèle KanbanList."""

import sys
import os
import pytest
import datetime
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.kanban_list import KanbanList

# Configuration de la base de données de test
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_kanban_list_model.db"
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


class TestKanbanListModel:
    """Tests pour le modèle KanbanList."""

    def test_model_creation(self):
        """Test de création du modèle KanbanList."""
        kanban_list = KanbanList()
        
        # Vérifier que l'objet est créé
        assert kanban_list is not None
        assert isinstance(kanban_list, KanbanList)

    def test_model_attributes(self):
        """Test que le modèle a tous les attributs attendus."""
        kanban_list = KanbanList()
        
        # Vérifier que tous les attributs existent
        assert hasattr(kanban_list, 'id')
        assert hasattr(kanban_list, 'name')
        assert hasattr(kanban_list, 'order')
        assert hasattr(kanban_list, 'created_at')
        assert hasattr(kanban_list, 'updated_at')

    def test_model_table_name(self):
        """Test que le nom de la table est correct."""
        assert KanbanList.__tablename__ == "kanban_lists"

    def test_create_kanban_list_successfully(self, db_session):
        """Test de création réussie d'une liste Kanban."""
        before_creation = datetime.datetime.now()
        
        kanban_list = KanbanList(
            name="Test List",
            order=1,
        )
        
        db_session.add(kanban_list)
        db_session.commit()
        db_session.refresh(kanban_list)
        
        after_creation = datetime.datetime.now()
        
        assert kanban_list.id is not None
        assert kanban_list.name == "Test List"
        assert kanban_list.order == 1
        assert kanban_list.created_at is not None
        assert kanban_list.updated_at is None
        
        # Vérifier que le timestamp est dans la plage attendue
        assert before_creation <= kanban_list.created_at <= after_creation

    def test_create_kanban_list_minimal(self, db_session):
        """Test de création avec les champs minimum requis."""
        kanban_list = KanbanList(
            name="Minimal List",
        )
        
        db_session.add(kanban_list)
        db_session.commit()
        db_session.refresh(kanban_list)
        
        assert kanban_list.id is not None
        assert kanban_list.name == "Minimal List"
        assert kanban_list.order is not None  # Devrait avoir une valeur par défaut

    def test_kanban_list_timestamps(self, db_session):
        """Test que les timestamps sont correctement gérés."""
        kanban_list = KanbanList(
            name="Timestamp Test",
            order=1,
        )
        
        db_session.add(kanban_list)
        db_session.commit()
        
        # Vérifier created_at
        assert kanban_list.created_at is not None
        assert isinstance(kanban_list.created_at, datetime.datetime)
        
        # Mettre à jour pour tester updated_at
        original_updated_at = kanban_list.updated_at
        kanban_list.name = "Updated Name"
        db_session.commit()
        db_session.refresh(kanban_list)
        
        # updated_at devrait maintenant être défini
        assert kanban_list.updated_at is not None
        assert isinstance(kanban_list.updated_at, datetime.datetime)
        assert kanban_list.updated_at != original_updated_at

    def test_kanban_list_update(self, db_session, sample_lists):
        """Test de mise à jour d'une liste Kanban."""
        kanban_list = sample_lists[0]
        original_created_at = kanban_list.created_at
        
        # Mettre à jour plusieurs champs
        kanban_list.name = "Updated List Name"
        kanban_list.order = 10
        
        db_session.commit()
        db_session.refresh(kanban_list)
        
        # Vérifier les mises à jour
        assert kanban_list.name == "Updated List Name"
        assert kanban_list.order == 10
        assert kanban_list.created_at == original_created_at  # Ne devrait pas changer
        assert kanban_list.updated_at is not None  # Devrait être mis à jour

    def test_kanban_list_query_by_name(self, db_session, sample_lists):
        """Test de recherche par nom."""
        kanban_list = db_session.query(KanbanList).filter(
            KanbanList.name == "To Do"
        ).first()
        
        assert kanban_list is not None
        assert kanban_list.name == "To Do"

    def test_kanban_list_query_by_order(self, db_session, sample_lists):
        """Test de recherche par ordre."""
        kanban_list = db_session.query(KanbanList).filter(
            KanbanList.order == 2
        ).first()
        
        assert kanban_list is not None
        assert kanban_list.order == 2

    def test_kanban_list_order_by_order(self, db_session, sample_lists):
        """Test de tri par ordre."""
        lists = db_session.query(KanbanList).order_by(
            KanbanList.order
        ).all()
        
        # Vérifier que les listes sont dans l'ordre croissant
        orders = [kanban_list.order for kanban_list in lists]
        assert orders == sorted(orders)

    def test_kanban_list_order_by_name(self, db_session, sample_lists):
        """Test de tri par nom."""
        lists = db_session.query(KanbanList).order_by(
            KanbanList.name
        ).all()
        
        # Vérifier que les noms sont en ordre alphabétique
        names = [kanban_list.name for kanban_list in lists]
        assert names == sorted(names)

    def test_kanban_list_search_by_name(self, db_session, sample_lists):
        """Test de recherche textuelle dans le nom."""
        # Créer des listes avec des noms spécifiques
        search_lists = [
            KanbanList(name="Backlog Tasks", order=4),
            KanbanList(name="Sprint Planning", order=5),
            KanbanList(name="Code Review", order=6),
        ]
        
        for kanban_list in search_lists:
            db_session.add(kanban_list)
        
        db_session.commit()
        
        # Rechercher les listes contenant "Tasks"
        task_lists = db_session.query(KanbanList).filter(
            KanbanList.name.like("%Tasks%")
        ).all()
        
        assert len(task_lists) == 1
        assert "Tasks" in task_lists[0].name

    def test_kanban_list_delete(self, db_session, sample_lists):
        """Test de suppression d'une liste Kanban."""
        kanban_list = sample_lists[0]
        list_id = kanban_list.id
        
        db_session.delete(kanban_list)
        db_session.commit()
        
        # Vérifier que la liste a été supprimée
        deleted_list = db_session.query(KanbanList).filter(
            KanbanList.id == list_id
        ).first()
        assert deleted_list is None

    def test_kanban_list_string_fields_validation(self, db_session):
        """Test des validations des champs texte."""
        # Test avec nom à la limite de la longueur
        max_length_name = "x" * 100  # Longueur maximale selon le modèle
        
        kanban_list = KanbanList(
            name=max_length_name,
            order=1,
        )
        
        db_session.add(kanban_list)
        db_session.commit()
        
        assert kanban_list.name == max_length_name
        assert len(kanban_list.name) == 100

    def test_kanban_list_special_characters(self, db_session):
        """Test avec des caractères spéciaux."""
        kanban_list = KanbanList(
            name="Liste spéciale: éèàçù 🚀 中文",
            order=1,
        )
        
        db_session.add(kanban_list)
        db_session.commit()
        
        assert kanban_list.name == "Liste spéciale: éèàçù 🚀 中文"

    def test_kanban_list_unicode_emojis(self, db_session):
        """Test avec des emojis Unicode."""
        kanban_list = KanbanList(
            name="Emoji List 🎯🚀✨",
            order=1,
        )
        
        db_session.add(kanban_list)
        db_session.commit()
        
        assert kanban_list.name == "Emoji List 🎯🚀✨"

    def test_kanban_list_empty_name(self, db_session):
        """Test avec un nom vide."""
        kanban_list = KanbanList(
            name="",
            order=1,
        )
        
        db_session.add(kanban_list)
        db_session.commit()
        
        assert kanban_list.name == ""

    def test_kanban_list_whitespace_only(self, db_session):
        """Test avec un nom ne contenant que des espaces."""
        kanban_list = KanbanList(
            name="   ",
            order=1,
        )
        
        db_session.add(kanban_list)
        db_session.commit()
        
        assert kanban_list.name == "   "

    def test_kanban_list_order_management(self, db_session):
        """Test de gestion des ordres."""
        # Créer des listes avec des ordres variés
        orders = [10, 5, 15, 1, 20]
        
        for i, order in enumerate(orders):
            kanban_list = KanbanList(
                name=f"Order Test {i}",
                order=order,
            )
            db_session.add(kanban_list)
        
        db_session.commit()
        
        # Récupérer les listes triées par ordre
        sorted_lists = db_session.query(KanbanList).order_by(
            KanbanList.order
        ).all()
        
        # Vérifier que les ordres sont en ordre croissant
        for i in range(len(sorted_lists) - 1):
            assert sorted_lists[i].order <= sorted_lists[i + 1].order

    def test_kanban_list_negative_order(self, db_session):
        """Test avec des ordres négatifs."""
        kanban_list = KanbanList(
            name="Negative Order Test",
            order=-5,
        )
        
        db_session.add(kanban_list)
        db_session.commit()
        
        assert kanban_list.order == -5

    def test_kanban_list_zero_order(self, db_session):
        """Test avec ordre zéro."""
        kanban_list = KanbanList(
            name="Zero Order Test",
            order=0,
        )
        
        db_session.add(kanban_list)
        db_session.commit()
        
        assert kanban_list.order == 0

    def test_kanban_list_large_order(self, db_session):
        """Test avec des ordres très grands."""
        kanban_list = KanbanList(
            name="Large Order Test",
            order=999999,
        )
        
        db_session.add(kanban_list)
        db_session.commit()
        
        assert kanban_list.order == 999999

    def test_kanban_list_duplicate_orders(self, db_session):
        """Test avec des ordres dupliqués."""
        list1 = KanbanList(name="List 1", order=5)
        list2 = KanbanList(name="List 2", order=5)
        
        db_session.add(list1)
        db_session.add(list2)
        db_session.commit()
        
        # Les deux listes devraient exister avec le même ordre
        assert list1.id is not None
        assert list2.id is not None
        assert list1.order == list2.order

    def test_kanban_list_batch_operations(self, db_session):
        """Test d'opérations par lots."""
        # Créer plusieurs listes en lot
        lists = []
        for i in range(10):
            kanban_list = KanbanList(
                name=f"Batch List {i}",
                order=i,
            )
            lists.append(kanban_list)
        
        db_session.add_all(lists)
        db_session.commit()
        
        # Vérifier que toutes ont été créées
        count = db_session.query(KanbanList).filter(
            KanbanList.name.like("Batch List %")
        ).count()
        assert count == 10

    def test_kanban_list_bulk_update(self, db_session, sample_lists):
        """Test de mises à jour en masse."""
        # Ajouter un préfixe à tous les noms de liste
        db_session.query(KanbanList).update({
            "name": KanbanList.name + " (Updated)"
        })
        
        db_session.commit()
        
        # Vérifier que tous les noms ont été mis à jour
        updated_lists = db_session.query(KanbanList).all()
        
        for kanban_list in updated_lists:
            assert "(Updated)" in kanban_list.name

    def test_kanban_list_complex_queries(self, db_session):
        """Test de requêtes complexes."""
        # Créer des listes variées
        lists_data = [
            ("Backlog", 1),
            ("To Do", 2),
            ("In Progress", 3),
            ("Review", 4),
            ("Done", 5),
        ]
        
        for name, order in lists_data:
            kanban_list = KanbanList(name=name, order=order)
            db_session.add(kanban_list)
        
        db_session.commit()
        
        # Chercher les listes avec ordre entre 2 et 4
        from sqlalchemy import and_
        
        middle_lists = db_session.query(KanbanList).filter(
            and_(
                KanbanList.order >= 2,
                KanbanList.order <= 4
            )
        ).order_by(KanbanList.order).all()
        
        assert len(middle_lists) == 3
        expected_names = ["To Do", "In Progress", "Review"]
        actual_names = [kanban_list.name for kanban_list in middle_lists]
        assert actual_names == expected_names

    def test_kanban_list_pagination(self, db_session):
        """Test de pagination des résultats."""
        # Créer plusieurs listes
        for i in range(20):
            kanban_list = KanbanList(
                name=f"Pagination List {i}",
                order=i,
            )
            db_session.add(kanban_list)
        
        db_session.commit()
        
        # Test pagination
        page1 = db_session.query(KanbanList).limit(5).all()
        page2 = db_session.query(KanbanList).offset(5).limit(5).all()
        
        assert len(page1) == 5
        assert len(page2) == 5
        assert page1[0].id != page2[0].id

    def test_kanban_list_count_aggregations(self, db_session):
        """Test d'agrégations et de comptage."""
        # Créer des listes
        for i in range(5):
            kanban_list = KanbanList(
                name=f"Count List {i}",
                order=i,
            )
            db_session.add(kanban_list)
        
        db_session.commit()
        
        # Compter le nombre total de listes
        total_count = db_session.query(KanbanList).count()
        assert total_count >= 5

    def test_kanban_list_error_handling(self, db_session):
        """Test de gestion des erreurs."""
        # Simuler une erreur de base de données
        with patch.object(db_session, 'commit', side_effect=SQLAlchemyError("Database error")):
            kanban_list = KanbanList(
                name="Error Test",
                order=1,
            )
            
            db_session.add(kanban_list)
            with pytest.raises(SQLAlchemyError):
                db_session.commit()

    def test_kanban_list_representation(self, db_session):
        """Test de la représentation textuelle de l'objet."""
        kanban_list = KanbanList(
            name="Representation Test",
            order=1,
        )
        
        db_session.add(kanban_list)
        db_session.commit()
        
        # La représentation devrait contenir des informations utiles
        str_repr = str(kanban_list)
        assert "KanbanList" in str_repr

    def test_kanban_list_equality(self, db_session):
        """Test de l'égalité entre objets."""
        list1 = KanbanList(name="Equality Test 1", order=1)
        list2 = KanbanList(name="Equality Test 2", order=2)
        
        db_session.add(list1)
        db_session.add(list2)
        db_session.commit()
        
        # Ce sont des objets différents
        assert list1 != list2
        assert list1.id != list2.id

    def test_kanban_list_database_constraints(self, db_session):
        """Test des contraintes de base de données."""
        # Test que name ne peut pas être NULL
        kanban_list = KanbanList(
            name=None,  # Devrait échouer
            order=1,
        )
        
        db_session.add(kanban_list)
        with pytest.raises(Exception):
            db_session.commit()

    def test_kanban_list_name_length_constraint(self, db_session):
        """Test de la contrainte de longueur du nom."""
        # Le modèle limite le nom à 100 caractères
        exact_length_name = "x" * 100
        
        kanban_list = KanbanList(
            name=exact_length_name,
            order=1,
        )
        
        db_session.add(kanban_list)
        db_session.commit()
        
        assert len(kanban_list.name) == 100
        assert kanban_list.name == exact_length_name

    def test_kanban_list_workflow_sequences(self, db_session):
        """Test des séquences de workflow typiques."""
        # Créer une séquence de workflow typique
        workflow_sequences = [
            ("Backlog", 0),
            ("To Do", 1),
            ("In Progress", 2),
            ("In Review", 3),
            ("Testing", 4),
            ("Done", 5),
        ]
        
        created_lists = []
        for name, order in workflow_sequences:
            kanban_list = KanbanList(name=name, order=order)
            db_session.add(kanban_list)
            created_lists.append(kanban_list)
        
        db_session.commit()
        
        # Vérifier que la séquence est correcte
        workflow_lists = db_session.query(KanbanList).order_by(
            KanbanList.order
        ).all()
        
        actual_names = [kanban_list.name for kanban_list in workflow_lists[-len(workflow_sequences):]]
        expected_names = [name for name, _ in workflow_sequences]
        
        assert actual_names == expected_names

    def test_kanban_list_reordering(self, db_session):
        """Test du réordonnancement des listes."""
        # Créer des listes avec des ordres initiaux
        original_lists = []
        for i in range(3):
            kanban_list = KanbanList(
                name=f"Original {i}",
                order=i * 10,  # 0, 10, 20
            )
            db_session.add(kanban_list)
            original_lists.append(kanban_list)
        
        db_session.commit()
        
        # Réordonner : échanger les positions
        original_lists[0].order = 20
        original_lists[2].order = 0
        
        db_session.commit()
        
        # Vérifier le nouvel ordre
        reordered_lists = db_session.query(KanbanList).order_by(
            KanbanList.order
        ).all()
        
        expected_names = ["Original 2", "Original 1", "Original 0"]
        actual_names = [kanban_list.name for kanban_list in reordered_lists]
        
        assert actual_names == expected_names

    def test_kanban_list_data_types(self, db_session):
        """Test avec différents types de données."""
        test_lists = [
            ("simple_name", "Simple List"),
            ("unicode_name", "Liste: éèàçù 中文"),
            ("emoji_name", "Emoji List 🎯🚀✨"),
            ("html_name", "<b>HTML</b> List"),
            ("long_name", "x" * 99),  # Juste sous la limite
            ("special_chars", "!@#$%^&*()_+-=[]{}|;':\",./<>?"),
            ("numbers_and_text", "List 123: Something"),
        ]
        
        for suffix, name in test_lists:
            kanban_list = KanbanList(
                name=name,
                order=len(test_lists),
            )
            db_session.add(kanban_list)
        
        db_session.commit()
        
        # Vérifier que toutes les listes ont été créées
        count = db_session.query(KanbanList).count()
        assert count >= len(test_lists)