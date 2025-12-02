"""Tests complets pour le modèle CardComment."""

import datetime
import os
import sys
from unittest.mock import patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base
from app.models.card import Card
from app.models.card_comment import CardComment, get_system_timezone_datetime
from app.models.kanban_list import KanbanList
from app.models.user import User, UserRole, UserStatus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configuration de la base de données de test
TEST_DB_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(TEST_DB_DIR, exist_ok=True)
TEST_DB_PATH = os.path.join(TEST_DB_DIR, "test_card_comment_model.db")
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
def sample_comments(db_session, sample_card, sample_user):
    """Fixture pour créer des commentaires de test."""
    comments = [
        CardComment(
            card_id=sample_card.id,
            user_id=sample_user.id,
            comment="First comment",
            is_deleted=False,
        ),
        CardComment(
            card_id=sample_card.id,
            user_id=sample_user.id,
            comment="Second comment",
            is_deleted=False,
        ),
        CardComment(
            card_id=sample_card.id,
            user_id=sample_user.id,
            comment="Deleted comment",
            is_deleted=True,
        ),
    ]

    for comment in comments:
        db_session.add(comment)
    db_session.commit()

    for comment in comments:
        db_session.refresh(comment)

    return comments


class TestGetSystemTimezoneDatetime:
    """Tests pour la fonction get_system_timezone_datetime."""

    def test_get_system_timezone_datetime(self):
        """Test de récupération de la date et heure actuelle."""
        result = get_system_timezone_datetime()

        assert isinstance(result, datetime.datetime)
        assert result.tzinfo is not None

        # La date devrait être récente
        now = datetime.datetime.now().astimezone()
        time_diff = abs((result - now).total_seconds())
        assert time_diff < 60  # Moins d'une minute de différence

    def test_get_system_timezone_datetime_multiple_calls(self):
        """Test que plusieurs appels retournent des heures différentes."""
        result1 = get_system_timezone_datetime()

        # Attendre un peu
        import time

        time.sleep(0.01)

        result2 = get_system_timezone_datetime()

        # Les deux devraient être différents
        assert result1 != result2
        assert result2 > result1

    def test_get_system_timezone_datetime_timezone_info(self):
        """Test que la timezone est correctement configurée."""
        result = get_system_timezone_datetime()

        # Vérifier que l'objet a une timezone
        assert result.tzinfo is not None

        # Convertir en UTC pour comparaison
        utc_now = datetime.datetime.now(datetime.timezone.utc)
        local_time = result.astimezone(datetime.timezone.utc)

        # La différence devrait être raisonnable (moins de 1 minute)
        time_diff = abs((local_time - utc_now).total_seconds())
        assert time_diff < 60


class TestCardCommentModel:
    """Tests pour le modèle CardComment."""

    def test_model_creation(self):
        """Test de création du modèle CardComment."""
        comment = CardComment()

        # Vérifier que l'objet est créé
        assert comment is not None
        assert isinstance(comment, CardComment)

    def test_model_attributes(self):
        """Test que le modèle a tous les attributs attendus."""
        comment = CardComment()

        # Vérifier que tous les attributs existent
        assert hasattr(comment, "id")
        assert hasattr(comment, "card_id")
        assert hasattr(comment, "user_id")
        assert hasattr(comment, "comment")
        assert hasattr(comment, "is_deleted")
        assert hasattr(comment, "created_at")
        assert hasattr(comment, "updated_at")
        assert hasattr(comment, "PROTECTED_FIELDS")

    def test_model_table_name(self):
        """Test que le nom de la table est correct."""
        assert CardComment.__tablename__ == "card_comments"

    def test_protected_fields(self):
        """Test que les champs protégés sont correctement définis."""
        expected_protected_fields = {"id", "card_id", "user_id", "created_at"}
        assert CardComment.PROTECTED_FIELDS == expected_protected_fields

    def test_create_card_comment_successfully(self, db_session, sample_card, sample_user):
        """Test de création réussie d'un commentaire."""
        before_creation = get_system_timezone_datetime()

        comment = CardComment(
            card_id=sample_card.id,
            user_id=sample_user.id,
            comment="Test comment",
            is_deleted=False,
        )

        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        after_creation = get_system_timezone_datetime()

        assert comment.id is not None
        assert comment.card_id == sample_card.id
        assert comment.user_id == sample_user.id
        assert comment.comment == "Test comment"
        assert comment.is_deleted is False
        assert comment.created_at is not None
        assert comment.updated_at is not None

        # Vérifier que les timestamps sont dans la plage attendue
        assert before_creation <= comment.created_at.astimezone() <= after_creation
        assert before_creation <= comment.updated_at.astimezone() <= after_creation

    def test_create_card_comment_minimal(self, db_session, sample_card, sample_user):
        """Test de création avec les champs minimum requis."""
        comment = CardComment(
            card_id=sample_card.id,
            user_id=sample_user.id,
            comment="Minimal comment",
        )

        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        assert comment.id is not None
        assert comment.card_id == sample_card.id
        assert comment.user_id == sample_user.id
        assert comment.comment == "Minimal comment"
        assert comment.is_deleted is False  # Valeur par défaut
        assert comment.created_at is not None
        assert comment.updated_at is not None

    def test_create_card_comment_deleted(self, db_session, sample_card, sample_user):
        """Test de création d'un commentaire supprimé."""
        comment = CardComment(
            card_id=sample_card.id,
            user_id=sample_user.id,
            comment="Deleted comment",
            is_deleted=True,
        )

        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        assert comment.is_deleted is True

    def test_card_comment_timestamps_on_create(self, db_session, sample_card, sample_user):
        """Test que les timestamps sont corrects à la création."""
        before_creation = get_system_timezone_datetime()

        comment = CardComment(
            card_id=sample_card.id,
            user_id=sample_user.id,
            comment="Timestamp test",
        )

        db_session.add(comment)
        db_session.commit()

        after_creation = get_system_timezone_datetime()

        # created_at et updated_at devraient être identiques à la création
        assert comment.created_at == comment.updated_at
        assert before_creation <= comment.created_at.astimezone() <= after_creation

    def test_card_comment_timestamp_on_update(self, db_session, sample_card, sample_user):
        """Test que le timestamp updated_at est mis à jour lors de la modification."""
        comment = CardComment(
            card_id=sample_card.id,
            user_id=sample_user.id,
            comment="Original comment",
        )

        db_session.add(comment)
        db_session.commit()

        original_created_at = comment.created_at
        original_updated_at = comment.updated_at

        # Attendre un peu pour s'assurer que le timestamp change
        import time

        time.sleep(0.5)

        # Mettre à jour le commentaire
        comment.comment = "Updated comment"
        db_session.commit()
        db_session.refresh(comment)

        # created_at ne devrait pas changer
        assert comment.created_at == original_created_at

        # updated_at devrait être différent et plus récent
        assert comment.updated_at != original_updated_at
        assert comment.updated_at is not None and original_updated_at is not None
        assert comment.updated_at > original_updated_at

    def test_card_comment_update(self, db_session, sample_card, sample_user):
        """Test de mise à jour d'un commentaire."""
        comment = CardComment(
            card_id=sample_card.id,
            user_id=sample_user.id,
            comment="Original comment",
            is_deleted=False,
        )

        db_session.add(comment)
        db_session.commit()

        original_created_at = comment.created_at

        # Mettre à jour plusieurs champs
        comment.comment = "Updated comment"
        comment.is_deleted = True

        db_session.commit()
        db_session.refresh(comment)

        # Vérifier les mises à jour
        assert comment.comment == "Updated comment"
        assert comment.is_deleted is True
        assert comment.created_at == original_created_at  # Ne devrait pas changer
        assert comment.updated_at is not None  # Devrait être mis à jour

    def test_card_comment_query_by_card(self, db_session, sample_card, sample_user):
        """Test de recherche par carte."""
        # Créer quelques commentaires
        for i in range(3):
            comment = CardComment(
                card_id=sample_card.id,
                user_id=sample_user.id,
                comment=f"Comment {i}",
            )
            db_session.add(comment)

        db_session.commit()

        # Rechercher les commentaires de la carte
        comments = db_session.query(CardComment).filter(CardComment.card_id == sample_card.id).all()

        assert len(comments) == 3
        assert all(comment.card_id == sample_card.id for comment in comments)

    def test_card_comment_query_by_user(self, db_session, sample_card, sample_user):
        """Test de recherche par utilisateur."""
        # Créer quelques commentaires
        for i in range(3):
            comment = CardComment(
                card_id=sample_card.id,
                user_id=sample_user.id,
                comment=f"User comment {i}",
            )
            db_session.add(comment)

        db_session.commit()

        # Rechercher les commentaires de l'utilisateur
        comments = db_session.query(CardComment).filter(CardComment.user_id == sample_user.id).all()

        assert len(comments) >= 3
        assert all(comment.user_id == sample_user.id for comment in comments)

    def test_card_comment_query_active_only(self, db_session, sample_comments):
        """Test de recherche des commentaires actifs uniquement."""
        active_comments = db_session.query(CardComment).filter(CardComment.is_deleted == False).all()

        assert len(active_comments) == 2  # Seulement les commentaires non supprimés
        assert all(not comment.is_deleted for comment in active_comments)

    def test_card_comment_query_deleted_only(self, db_session, sample_comments):
        """Test de recherche des commentaires supprimés uniquement."""
        deleted_comments = db_session.query(CardComment).filter(CardComment.is_deleted).all()

        assert len(deleted_comments) == 1
        assert all(comment.is_deleted for comment in deleted_comments)

    def test_card_comment_query_by_text(self, db_session, sample_card, sample_user):
        """Test de recherche textuelle dans les commentaires."""
        # Créer des commentaires avec du text spécifique
        comments = [
            CardComment(card_id=sample_card.id, user_id=sample_user.id, comment="Hello World"),
            CardComment(card_id=sample_card.id, user_id=sample_user.id, comment="Hello Python"),
            CardComment(card_id=sample_card.id, user_id=sample_user.id, comment="Goodbye World"),
        ]

        for comment in comments:
            db_session.add(comment)

        db_session.commit()

        # Rechercher les commentaires contenant "Hello"
        hello_comments = db_session.query(CardComment).filter(CardComment.comment.like("%Hello%")).all()

        assert len(hello_comments) == 2
        assert all("Hello" in comment.comment for comment in hello_comments)

    def test_card_comment_order_by_creation_date(self, db_session, sample_card, sample_user):
        """Test de tri par date de création."""
        # Créer des commentaires avec un délai
        comments = []
        for i in range(3):
            comment = CardComment(
                card_id=sample_card.id,
                user_id=sample_user.id,
                comment=f"Comment {i}",
            )
            db_session.add(comment)
            db_session.commit()
            comments.append(comment)

            # Attendre un peu
            import time

            time.sleep(0.01)

        # Récupérer les commentaires triés par date de création
        sorted_comments = db_session.query(CardComment).order_by(CardComment.created_at).all()

        # Vérifier qu'ils sont dans l'ordre chronologique
        for i in range(len(sorted_comments) - 1):
            assert sorted_comments[i].created_at <= sorted_comments[i + 1].created_at

    def test_card_comment_order_by_update_date(self, db_session, sample_card, sample_user):
        """Test de tri par date de mise à jour."""
        # Créer des commentaires
        comments = []
        for i in range(3):
            comment = CardComment(
                card_id=sample_card.id,
                user_id=sample_user.id,
                comment=f"Comment {i}",
            )
            db_session.add(comment)
            comments.append(comment)

        db_session.commit()

        # Mettre à jour les commentaires dans un ordre différent
        comments[2].comment = "Updated last"
        db_session.commit()

        import time

        time.sleep(0.01)

        comments[0].comment = "Updated first"
        db_session.commit()

        # Récupérer les commentaires triés par date de mise à jour
        sorted_comments = db_session.query(CardComment).order_by(CardComment.updated_at.desc()).all()

        # Le premier commentaire devrait être celui mis à jour en dernier
        assert sorted_comments[0].comment == "Updated first"

    def test_card_comment_delete(self, db_session, sample_comments):
        """Test de suppression d'un commentaire."""
        comment = sample_comments[0]
        comment_id = comment.id

        db_session.delete(comment)
        db_session.commit()

        # Vérifier que le commentaire a été supprimé
        deleted_comment = db_session.query(CardComment).filter(CardComment.id == comment_id).first()
        assert deleted_comment is None

    def test_card_comment_soft_delete(self, db_session, sample_card, sample_user):
        """Test de suppression logique (soft delete)."""
        comment = CardComment(
            card_id=sample_card.id,
            user_id=sample_user.id,
            comment="To be deleted",
            is_deleted=False,
        )

        db_session.add(comment)
        db_session.commit()

        # Faire une suppression logique
        comment.is_deleted = True
        db_session.commit()
        db_session.refresh(comment)

        # Le commentaire devrait toujours exister en base
        assert db_session.query(CardComment).filter(CardComment.id == comment.id).first() is not None

        # Mais ne devrait pas apparaître dans les requêtes actives
        active_comments = db_session.query(CardComment).filter(not CardComment.is_deleted).all()
        assert comment not in active_comments

    def test_card_comment_string_fields_validation(self, db_session, sample_card, sample_user):
        """Test des validations des champs text."""
        # Test avec commentaire long
        long_comment = "x" * 1000  # Longueur maximale raisonnable

        comment = CardComment(
            card_id=sample_card.id,
            user_id=sample_user.id,
            comment=long_comment,
        )

        db_session.add(comment)
        db_session.commit()

        assert comment.comment == long_comment

    def test_card_comment_special_characters(self, db_session, sample_card, sample_user):
        """Test avec des caractères spéciaux."""
        comment = CardComment(
            card_id=sample_card.id,
            user_id=sample_user.id,
            comment="Commentaire spécial: éèàçù 🚀 中文",
        )

        db_session.add(comment)
        db_session.commit()

        assert comment.comment == "Commentaire spécial: éèàçù 🚀 中文"

    def test_card_comment_unicode_emojis(self, db_session, sample_card, sample_user):
        """Test avec des emojis Unicode."""
        comment = CardComment(
            card_id=sample_card.id,
            user_id=sample_user.id,
            comment="Emoji Test 🎯🚀✨ 😊 👍",
        )

        db_session.add(comment)
        db_session.commit()

        assert comment.comment == "Emoji Test 🎯🚀✨ 😊 👍"

    def test_card_comment_html_content(self, db_session, sample_card, sample_user):
        """Test avec contenu HTML."""
        html_content = "<div>HTML Content</div><script>alert('test')</script><p>Paragraph</p>"

        comment = CardComment(
            card_id=sample_card.id,
            user_id=sample_user.id,
            comment=html_content,
        )

        db_session.add(comment)
        db_session.commit()

        # Le contenu HTML devrait être stocké tel quel
        assert comment.comment == html_content

    def test_card_comment_empty_comment(self, db_session, sample_card, sample_user):
        """Test avec un commentaire vide."""
        comment = CardComment(
            card_id=sample_card.id,
            user_id=sample_user.id,
            comment="",
        )

        db_session.add(comment)
        db_session.commit()

        assert comment.comment == ""

    def test_card_comment_whitespace_only(self, db_session, sample_card, sample_user):
        """Test avec un commentaire ne contenant que des espaces."""
        comment = CardComment(
            card_id=sample_card.id,
            user_id=sample_user.id,
            comment="   ",
        )

        db_session.add(comment)
        db_session.commit()

        assert comment.comment == "   "

    def test_card_comment_multiline_text(self, db_session, sample_card, sample_user):
        """Test avec du text multiligne."""
        multiline_text = """This is a multiline comment.
Line 2
Line 3
With some special characters: éèàç"""

        comment = CardComment(
            card_id=sample_card.id,
            user_id=sample_user.id,
            comment=multiline_text,
        )

        db_session.add(comment)
        db_session.commit()

        assert comment.comment == multiline_text

    def test_card_comment_null_fields(self, db_session, sample_card, sample_user):
        """Test avec des champs NULL."""
        comment = CardComment(
            card_id=sample_card.id,
            user_id=sample_user.id,
            comment="Null fields test",
        )

        db_session.add(comment)
        db_session.commit()

        # Les champs optionnels devraient être None ou avoir des valeurs par défaut
        assert comment.is_deleted is False  # Valeur par défaut
        assert comment.created_at is not None
        assert comment.updated_at is not None

    def test_card_comment_foreign_key_constraints(self, db_session, sample_user):
        """Test des contraintes de clé étrangère."""
        # Essayer de créer un commentaire avec un card_id invalide
        comment = CardComment(
            card_id=99999,  # N'existe pas
            user_id=sample_user.id,
            comment="Invalid card test",
        )

        db_session.add(comment)
        # Peut échouer selon la configuration de la base de données
        try:
            db_session.commit()
        except Exception:
            db_session.rollback()

        db_session.rollback()

        # Essayer de créer un commentaire avec un user_id invalide
        comment = CardComment(
            card_id=1,  # Supposer que la carte 1 existe
            user_id=99999,  # N'existe pas
            comment="Invalid user test",
        )

        db_session.add(comment)
        try:
            db_session.commit()
        except Exception:
            db_session.rollback()

    def test_card_comment_relationships_loading(self, db_session, sample_comments, sample_card, sample_user):
        """Test que les relations sont correctement chargées."""
        comment = sample_comments[0]

        # Charger la relation card
        assert comment.card is not None
        assert comment.card.id == comment.card_id

        # Charger la relation user
        assert comment.user is not None
        assert comment.user.id == comment.user_id

    def test_card_comment_cascade_delete(self, db_session, sample_card, sample_user):
        """Test de la suppression en cascade."""
        # Créer un commentaire
        comment = CardComment(
            card_id=sample_card.id,
            user_id=sample_user.id,
            comment="Cascade test",
        )

        db_session.add(comment)
        db_session.commit()

        comment_id = comment.id

        # Supprimer la carte
        db_session.delete(sample_card)
        db_session.commit()

        # Le commentaire devrait être supprimé en cascade
        deleted_comment = db_session.query(CardComment).filter(CardComment.id == comment_id).first()
        assert deleted_comment is None

    def test_card_comment_batch_operations(self, db_session, sample_card, sample_user):
        """Test d'opérations par lots."""
        # Créer plusieurs commentaires en lot
        comments = []
        for i in range(10):
            comment = CardComment(
                card_id=sample_card.id,
                user_id=sample_user.id,
                comment=f"Batch comment {i}",
            )
            comments.append(comment)

        db_session.add_all(comments)
        db_session.commit()

        # Vérifier que tous ont été créés
        count = db_session.query(CardComment).filter(CardComment.comment.like("Batch comment %")).count()
        assert count == 10

    def test_card_comment_bulk_update(self, db_session, sample_comments):
        """Test de mises à jour en masse."""
        # Mettre à jour tous les commentaires non supprimés pour les marquer comme supprimés
        db_session.query(CardComment).filter(not CardComment.is_deleted).update({"is_deleted": True})

        db_session.commit()

        # Vérifier que tous les commentaires sont maintenant supprimés
        active_comments = db_session.query(CardComment).filter(not CardComment.is_deleted).count()
        assert active_comments == 0

    def test_card_comment_complex_queries(self, db_session, sample_card, sample_user):
        """Test de requêtes complexes."""
        # Créer des commentaires variés
        import time

        comment1 = CardComment(
            card_id=sample_card.id,
            user_id=sample_user.id,
            comment="Important comment",
            is_deleted=False,
        )
        db_session.add(comment1)
        db_session.commit()

        time.sleep(0.01)

        comment2 = CardComment(
            card_id=sample_card.id,
            user_id=sample_user.id,
            comment="Another comment",
            is_deleted=False,
        )
        db_session.add(comment2)
        db_session.commit()

        time.sleep(0.01)

        comment3 = CardComment(
            card_id=sample_card.id,
            user_id=sample_user.id,
            comment="Deleted comment",
            is_deleted=True,
        )
        db_session.add(comment3)
        db_session.commit()

        # Chercher les commentaires actifs contenant "comment"
        from sqlalchemy import and_

        comments = (
            db_session.query(CardComment)
            .filter(and_(CardComment.is_deleted == False, CardComment.comment.like("%comment%")))
            .order_by(CardComment.created_at.desc())
            .all()
        )

        assert len(comments) == 2
        assert all("comment" in c.comment for c in comments)

    def test_card_comment_pagination(self, db_session, sample_card, sample_user):
        """Test de pagination des résultats."""
        # Créer plusieurs commentaires
        for i in range(20):
            comment = CardComment(
                card_id=sample_card.id,
                user_id=sample_user.id,
                comment=f"Pagination comment {i}",
            )
            db_session.add(comment)

        db_session.commit()

        # Test pagination
        page1 = db_session.query(CardComment).limit(5).all()
        page2 = db_session.query(CardComment).offset(5).limit(5).all()

        assert len(page1) == 5
        assert len(page2) == 5
        assert page1[0].id != page2[0].id

    def test_card_comment_count_aggregations(self, db_session, sample_card, sample_user):
        """Test d'agrégations et de comptage."""
        # Créer des commentaires avec différents états
        for i in range(5):
            comment = CardComment(
                card_id=sample_card.id,
                user_id=sample_user.id,
                comment=f"Active comment {i}",
                is_deleted=False,
            )
            db_session.add(comment)

        for i in range(3):
            comment = CardComment(
                card_id=sample_card.id,
                user_id=sample_user.id,
                comment=f"Deleted comment {i}",
                is_deleted=True,
            )
            db_session.add(comment)

        db_session.commit()

        # Compter les commentaires par statut
        active_count = db_session.query(CardComment).filter(CardComment.is_deleted == False).count()

        deleted_count = db_session.query(CardComment).filter(CardComment.is_deleted).count()

        assert active_count == 5
        assert deleted_count == 3

    def test_card_comment_error_handling(self, db_session, sample_card, sample_user):
        """Test de gestion des erreurs."""
        # Simuler une erreur de base de données
        with patch.object(db_session, "commit", side_effect=SQLAlchemyError("Database error")):
            comment = CardComment(
                card_id=sample_card.id,
                user_id=sample_user.id,
                comment="Error test",
            )

            db_session.add(comment)
            with pytest.raises(SQLAlchemyError):
                db_session.commit()

    def test_card_comment_representation(self, db_session, sample_card, sample_user):
        """Test de la représentation textuelle de l'objet."""
        comment = CardComment(
            card_id=sample_card.id,
            user_id=sample_user.id,
            comment="Representation test",
        )

        db_session.add(comment)
        db_session.commit()

        # La représentation devrait contenir des informations utiles
        str_repr = str(comment)
        assert "CardComment" in str_repr

    def test_card_comment_equality(self, db_session, sample_card, sample_user):
        """Test de l'égalité entre objets."""
        comment1 = CardComment(
            card_id=sample_card.id,
            user_id=sample_user.id,
            comment="Equality test 1",
        )

        comment2 = CardComment(
            card_id=sample_card.id,
            user_id=sample_user.id,
            comment="Equality test 2",
        )

        db_session.add(comment1)
        db_session.add(comment2)
        db_session.commit()

        # Ce sont des objets différents
        assert comment1 != comment2
        assert comment1.id != comment2.id

    def test_card_comment_unique_constraints(self, db_session, sample_card, sample_user):
        """Test des contraintes d'unicité."""
        # Le modèle CardComment n'a pas de contraintes d'unicité spécifiques
        # plusieurs commentaires peuvent avoir le même contenu
        comment1 = CardComment(
            card_id=sample_card.id,
            user_id=sample_user.id,
            comment="Same content",
        )

        comment2 = CardComment(
            card_id=sample_card.id,
            user_id=sample_user.id,
            comment="Same content",
        )

        db_session.add(comment1)
        db_session.add(comment2)
        db_session.commit()

        # Les deux commentaires devraient exister
        assert comment1.id is not None
        assert comment2.id is not None
        assert comment1.comment == comment2.comment

    def test_card_comment_database_constraints(self, db_session):
        """Test des contraintes de base de données."""
        # Test que card_id ne peut pas être NULL
        comment = CardComment(
            card_id=None,  # Devrait échouer
            user_id=1,
            comment="Test",
        )

        db_session.add(comment)
        with pytest.raises(Exception):
            db_session.commit()

        db_session.rollback()

        # Test que user_id ne peut pas être NULL
        comment = CardComment(
            card_id=1,
            user_id=None,  # Devrait échouer
            comment="Test",
        )

        db_session.add(comment)
        with pytest.raises(Exception):
            db_session.commit()

        db_session.rollback()

        # Test que comment ne peut pas être NULL
        comment = CardComment(
            card_id=1,
            user_id=1,
            comment=None,  # Devrait échouer
        )

        db_session.add(comment)
        with pytest.raises(Exception):
            db_session.commit()

    def test_card_comment_transactions(self, db_session, sample_card, sample_user):
        """Test de transactions."""
        # Créer un commentaire
        comment = CardComment(
            card_id=sample_card.id,
            user_id=sample_user.id,
            comment="Transaction test",
        )
        db_session.add(comment)
        db_session.commit()

        original_comment = comment.comment

        # Modifier dans une transaction
        comment.comment = "Modified comment"

        # Faire un rollback
        db_session.rollback()
        db_session.refresh(comment)

        # Le commentaire devrait être celui d'avant la modification
        assert comment.comment == original_comment

    def test_card_comment_concurrent_modification(self, db_session, sample_card, sample_user):
        """Test de modification concurrente (simplifié)."""
        # Créer un commentaire
        comment = CardComment(
            card_id=sample_card.id,
            user_id=sample_user.id,
            comment="Concurrent test",
        )
        db_session.add(comment)
        db_session.commit()

        # Simuler des modifications concurrentes
        comment1 = db_session.query(CardComment).filter(CardComment.id == comment.id).first()
        comment2 = db_session.query(CardComment).filter(CardComment.id == comment.id).first()

        # Les deux devraient être le même objet
        assert comment1.id == comment2.id

        # Modifier à travers la première référence
        comment1.comment = "Concurrent modification 1"
        db_session.commit()

        # Rafraîchir la deuxième référence
        db_session.refresh(comment2)

        # La deuxième référence devrait voir la modification
        assert comment2.comment == "Concurrent modification 1"

    def test_card_comment_session_isolation(self, db_session, sample_card, sample_user):
        """Test d'isolation des sessions."""
        # Créer un commentaire
        comment = CardComment(
            card_id=sample_card.id,
            user_id=sample_user.id,
            comment="Session test",
        )
        db_session.add(comment)

        # Ne pas commiter encore
        # L'objet ne devrait pas être visible dans une nouvelle session
        new_session = TestingSessionLocal()
        try:
            count = new_session.query(CardComment).filter(CardComment.comment == "Session test").count()
            assert count == 0
        finally:
            new_session.close()

        # Commiter maintenant
        db_session.commit()

        # Maintenant il devrait être visible
        new_session = TestingSessionLocal()
        try:
            count = new_session.query(CardComment).filter(CardComment.comment == "Session test").count()
            assert count == 1
        finally:
            new_session.close()

    def test_card_comment_relationships_eager_loading(self, db_session, sample_card, sample_user):
        """Test du chargement eager des relations."""
        from sqlalchemy.orm import joinedload

        # Créer un commentaire
        comment = CardComment(
            card_id=sample_card.id,
            user_id=sample_user.id,
            comment="Eager loading test",
        )
        db_session.add(comment)
        db_session.commit()

        # Charger avec relations eager
        loaded_comment = (
            db_session.query(CardComment)
            .options(joinedload(CardComment.card), joinedload(CardComment.user))
            .filter(CardComment.id == comment.id)
            .first()
        )

        assert loaded_comment is not None
        assert loaded_comment.card is not None
        assert loaded_comment.user is not None

    def test_card_comment_filtering_combined(self, db_session, sample_card, sample_user):
        """Test de filtrage combiné."""
        # Créer des commentaires variés
        comments = [
            CardComment(card_id=sample_card.id, user_id=sample_user.id, comment="Important active", is_deleted=False),
            CardComment(card_id=sample_card.id, user_id=sample_user.id, comment="Important deleted", is_deleted=True),
            CardComment(card_id=sample_card.id, user_id=sample_user.id, comment="Normal active", is_deleted=False),
        ]

        for comment in comments:
            db_session.add(comment)

        db_session.commit()

        # Chercher les commentaires actifs contenant "Important"
        from sqlalchemy import and_

        important_active = (
            db_session.query(CardComment)
            .filter(and_(CardComment.is_deleted == False, CardComment.comment.like("%Important%")))
            .all()
        )

        assert len(important_active) == 1
        assert important_active[0].comment == "Important active"

    def test_card_comment_data_types(self, db_session, sample_card, sample_user):
        """Test avec différents types de données."""
        test_comments = [
            ("string_simple", "Simple text"),
            ("unicode_test", "Unicode: éèàçù 中文"),
            ("emoji_test", "Emoji: 🚀🎯✨"),
            ("html_test", "<b>HTML</b> content"),
            ("long_text", "x" * 500),
            ("multiline", "Line 1\nLine 2\nLine 3"),
            ("special_chars", "!@#$%^&*()_+-=[]{}|;':\",./<>?"),
        ]

        for suffix, content in test_comments:
            comment = CardComment(
                card_id=sample_card.id,
                user_id=sample_user.id,
                comment=content,
            )
            db_session.add(comment)

        db_session.commit()

        # Vérifier que tous les commentaires ont été créés
        count = db_session.query(CardComment).count()
        assert count >= len(test_comments)
