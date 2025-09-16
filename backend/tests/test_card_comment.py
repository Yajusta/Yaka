"""Tests complets pour le service CardComment."""

import pytest
import sys
import os
from unittest.mock import patch
from datetime import datetime
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.card_comment import CardComment
from app.models.card import Card, CardPriority
from app.models.user import User, UserRole, UserStatus
from app.models.kanban_list import KanbanList
from app.schemas.card_comment import CardCommentCreate, CardCommentUpdate
from app.services.card_comment import (
    get_comments_for_card,
    create_comment,
    update_comment,
    delete_comment,
    get_comment_by_id,
)

# Configuration de la base de données de test
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_card_comment.db"
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
        titre="Test Card",
        description="Test Description",
        priorite=CardPriority.MEDIUM,
        list_id=sample_kanban_list.id,
        created_by=sample_user.id,
    )
    db_session.add(card)
    db_session.commit()
    db_session.refresh(card)
    return card


@pytest.fixture
def sample_comments(db_session, sample_card, sample_user, sample_user_2):
    """Fixture pour créer des commentaires de test."""
    comments = [
        CardComment(
            card_id=sample_card.id,
            user_id=sample_user.id,
            comment="Premier commentaire",
            is_deleted=False,
        ),
        CardComment(
            card_id=sample_card.id,
            user_id=sample_user_2.id,
            comment="Deuxième commentaire",
            is_deleted=False,
        ),
        CardComment(
            card_id=sample_card.id,
            user_id=sample_user.id,
            comment="Commentaire supprimé",
            is_deleted=True,
        ),
    ]
    
    for comment in comments:
        db_session.add(comment)
    db_session.commit()
    
    for comment in comments:
        db_session.refresh(comment)
    
    return comments


class TestGetCommentsForCard:
    """Tests pour la fonction get_comments_for_card."""

    def test_get_comments_success(self, db_session, sample_comments):
        """Test de récupération réussie des commentaires d'une carte."""
        card_id = sample_comments[0].card_id
        comments = get_comments_for_card(db_session, card_id)
        
        assert len(comments) == 2  # Seulement les commentaires non supprimés
        # Vérifier que les commentaires sont triés par date décroissante
        comments_sorted = sorted(comments, key=lambda x: x.created_at, reverse=True)
        assert comments[0].id == comments_sorted[0].id
        assert comments[1].id == comments_sorted[1].id
        assert all(not comment.is_deleted for comment in comments)
        assert all(hasattr(comment, 'user') for comment in comments)

    def test_get_comments_with_pagination(self, db_session, sample_card, sample_user):
        """Test de récupération avec pagination."""
        # Créer plusieurs commentaires
        for i in range(10):
            comment = CardComment(
                card_id=sample_card.id,
                user_id=sample_user.id,
                comment=f"Commentaire {i}",
                is_deleted=False,
            )
            db_session.add(comment)
        db_session.commit()
        
        # Test avec limit=5, offset=0
        comments_page1 = get_comments_for_card(db_session, sample_card.id, limit=5, offset=0)
        assert len(comments_page1) == 5
        
        # Test avec limit=5, offset=5
        comments_page2 = get_comments_for_card(db_session, sample_card.id, limit=5, offset=5)
        assert len(comments_page2) == 5
        
        # Vérifier que les commentaires sont différents
        page1_ids = [c.id for c in comments_page1]
        page2_ids = [c.id for c in comments_page2]
        assert len(set(page1_ids + page2_ids)) == 10  # Tous les IDs sont uniques

    def test_get_comments_empty(self, db_session, sample_card):
        """Test de récupération d'une carte sans commentaires."""
        comments = get_comments_for_card(db_session, sample_card.id)
        
        assert len(comments) == 0

    def test_get_comments_all_deleted(self, db_session, sample_card, sample_user):
        """Test de récupération d'une carte avec seulement des commentaires supprimés."""
        # Créer des commentaires supprimés
        for i in range(3):
            comment = CardComment(
                card_id=sample_card.id,
                user_id=sample_user.id,
                comment=f"Commentaire supprimé {i}",
                is_deleted=True,
            )
            db_session.add(comment)
        db_session.commit()
        
        comments = get_comments_for_card(db_session, sample_card.id)
        
        assert len(comments) == 0

    def test_get_comments_nonexistent_card(self, db_session):
        """Test de récupération de commentaires pour une carte inexistante."""
        comments = get_comments_for_card(db_session, 99999)
        
        assert len(comments) == 0

    def test_get_comments_multiple_cards(self, db_session, sample_kanban_list, sample_user):
        """Test de récupération de commentaires pour plusieurs cartes différentes."""
        # Créer deux cartes
        card1 = Card(
            titre="Card 1",
            description="Description 1",
            priorite=CardPriority.MEDIUM,
            list_id=sample_kanban_list.id,
            created_by=sample_user.id,
        )
        card2 = Card(
            titre="Card 2",
            description="Description 2",
            priorite=CardPriority.MEDIUM,
            list_id=sample_kanban_list.id,
            created_by=sample_user.id,
        )
        db_session.add(card1)
        db_session.add(card2)
        db_session.commit()
        db_session.refresh(card1)
        db_session.refresh(card2)
        
        # Ajouter des commentaires à chaque carte
        comment1 = CardComment(card_id=card1.id, user_id=sample_user.id, comment="Card 1 Comment")
        comment2 = CardComment(card_id=card2.id, user_id=sample_user.id, comment="Card 2 Comment")
        db_session.add(comment1)
        db_session.add(comment2)
        db_session.commit()
        
        # Vérifier que chaque carte a ses propres commentaires
        comments1 = get_comments_for_card(db_session, card1.id)
        comments2 = get_comments_for_card(db_session, card2.id)
        
        assert len(comments1) == 1
        assert len(comments2) == 1
        assert comments1[0].comment == "Card 1 Comment"
        assert comments2[0].comment == "Card 2 Comment"

    def test_get_comments_user_relationship_loaded(self, db_session, sample_comments):
        """Test que la relation user est bien chargée."""
        card_id = sample_comments[0].card_id
        comments = get_comments_for_card(db_session, card_id)
        
        for comment in comments:
            assert comment.user is not None
            assert hasattr(comment.user, 'id')
            assert hasattr(comment.user, 'display_name')
            assert hasattr(comment.user, 'email')

    def test_get_comments_ordering(self, db_session, sample_card, sample_user):
        """Test que les commentaires sont bien triés par date décroissante."""
        # Créer des commentaires séquentiellement avec un petit délai
        import time
        
        comments = []
        for i in range(3):
            comment = CardComment(
                card_id=sample_card.id,
                user_id=sample_user.id,
                comment=f"Commentaire {i+1}",
                is_deleted=False,
            )
            db_session.add(comment)
            db_session.commit()
            db_session.refresh(comment)
            comments.append(comment)
            time.sleep(0.01)  # Petit délai pour assurer des dates différentes
        
        # Récupérer les commentaires
        retrieved_comments = get_comments_for_card(db_session, sample_card.id)
        
        assert len(retrieved_comments) == 3
        # Vérifier qu'ils sont triés par date décroissante
        for i in range(len(retrieved_comments) - 1):
            assert retrieved_comments[i].created_at >= retrieved_comments[i + 1].created_at


class TestCreateComment:
    """Tests pour la fonction create_comment."""

    def test_create_comment_success(self, db_session, sample_card, sample_user):
        """Test de création réussie d'un commentaire."""
        comment_data = CardCommentCreate(
            card_id=sample_card.id,
            comment="Nouveau commentaire de test"
        )
        
        result = create_comment(db_session, comment_data, sample_user.id)
        
        assert result.id is not None
        assert result.card_id == sample_card.id
        assert result.user_id == sample_user.id
        assert result.comment == "Nouveau commentaire de test"
        assert result.is_deleted is False
        assert result.created_at is not None
        assert result.user is not None
        assert result.user.id == sample_user.id

    def test_create_comment_nonexistent_card(self, db_session, sample_user):
        """Test de création d'un commentaire pour une carte inexistante."""
        comment_data = CardCommentCreate(
            card_id=99999,
            comment="Commentaire carte inexistante"
        )
        
        with pytest.raises(ValueError, match="Carte introuvable"):
            create_comment(db_session, comment_data, sample_user.id)

    def test_create_comment_nonexistent_user(self, db_session, sample_card):
        """Test de création d'un commentaire par un utilisateur inexistant."""
        comment_data = CardCommentCreate(
            card_id=sample_card.id,
            comment="Commentaire utilisateur inexistant"
        )
        
        with pytest.raises(ValueError, match="Utilisateur introuvable"):
            create_comment(db_session, comment_data, 99999)

    def test_create_comment_unicode_content(self, db_session, sample_card, sample_user):
        """Test de création avec contenu Unicode."""
        unicode_text = "Commentaire avec caractères spéciaux: éèàçù 🚀 中文"
        comment_data = CardCommentCreate(
            card_id=sample_card.id,
            comment=unicode_text
        )
        
        result = create_comment(db_session, comment_data, sample_user.id)
        
        assert result.comment == unicode_text

    def test_create_comment_max_length(self, db_session, sample_card, sample_user):
        """Test de création avec commentaire de longueur maximale."""
        max_text = "x" * 1000
        comment_data = CardCommentCreate(
            card_id=sample_card.id,
            comment=max_text
        )
        
        result = create_comment(db_session, comment_data, sample_user.id)
        
        assert result.comment == max_text

    def test_create_comment_integrity_error(self, db_session, sample_card, sample_user):
        """Test de gestion des erreurs d'intégrité."""
        comment_data = CardCommentCreate(
            card_id=sample_card.id,
            comment="Test d'intégrité"
        )
        
        with patch.object(db_session, 'commit', side_effect=IntegrityError("Mock error", {}, None)):
            with pytest.raises(ValueError, match="Erreur d'intégrité lors de la création du commentaire"):
                create_comment(db_session, comment_data, sample_user.id)

    def test_create_comment_reload_error(self, db_session, sample_card, sample_user):
        """Test de gestion d'erreur lors du rechargement."""
        comment_data = CardCommentCreate(
            card_id=sample_card.id,
            comment="Test rechargement"
        )
        
        with patch.object(db_session, 'query') as mock_query:
            mock_query.return_value.options.return_value.filter.return_value.first.return_value = None
            
            with pytest.raises(ValueError, match="Erreur lors de la création du commentaire"):
                create_comment(db_session, comment_data, sample_user.id)

    def test_create_comment_whitespace_content(self, db_session, sample_card, sample_user):
        """Test de création avec contenu qui n'est que des espaces."""
        comment_data = CardCommentCreate(
            card_id=sample_card.id,
            comment="   "
        )
        
        # Pydantic accepte les espaces (min_length=1), mais la logique métier pourrait les rejeter
        # Pour ce test, nous vérifions simplement que le commentaire est créé
        result = create_comment(db_session, comment_data, sample_user.id)
        assert result.comment == "   "

    def test_create_comment_very_long_comment(self, db_session, sample_card, sample_user):
        """Test de création avec un commentaire très long."""
        long_comment = "x" * 5000  # Dépasse la limite de 1000
        
        # La validation Pydantic devrait empêcher cela
        with pytest.raises(Exception):  # PydanticValidationError
            CardCommentCreate(
                card_id=sample_card.id,
                comment=long_comment
            )


class TestUpdateComment:
    """Tests pour la fonction update_comment."""

    def test_update_comment_success(self, db_session, sample_comments, sample_user):
        """Test de mise à jour réussie d'un commentaire."""
        comment = sample_comments[0]  # Premier commentaire par sample_user
        comment_update = CardCommentUpdate(comment="Commentaire mis à jour")
        
        result = update_comment(db_session, comment.id, comment_update, sample_user.id)
        
        assert result is not None
        assert result.comment == "Commentaire mis à jour"
        assert result.user is not None
        assert result.user.id == sample_user.id

    def test_update_comment_nonexistent(self, db_session, sample_user):
        """Test de mise à jour d'un commentaire inexistant."""
        comment_update = CardCommentUpdate(comment="Nouveau texte")
        
        with pytest.raises(ValueError, match="Commentaire introuvable"):
            update_comment(db_session, 99999, comment_update, sample_user.id)

    def test_update_comment_unauthorized_user(self, db_session, sample_comments, sample_user_2):
        """Test de mise à jour par un utilisateur non autorisé."""
        comment = sample_comments[0]  # Créé par sample_user
        comment_update = CardCommentUpdate(comment="Tentative de modification")
        
        with pytest.raises(ValueError, match="Vous ne pouvez modifier que vos propres commentaires"):
            update_comment(db_session, comment.id, comment_update, sample_user_2.id)

    def test_update_comment_deleted(self, db_session, sample_comments, sample_user):
        """Test de mise à jour d'un commentaire supprimé."""
        comment = sample_comments[2]  # Commentaire supprimé par sample_user
        comment_update = CardCommentUpdate(comment="Tentative de modification")
        
        with pytest.raises(ValueError, match="Impossible de modifier un commentaire supprimé"):
            update_comment(db_session, comment.id, comment_update, sample_user.id)

    def test_update_comment_protected_fields(self, db_session, sample_comments, sample_user):
        """Test que les champs protégés ne sont pas modifiés."""
        comment = sample_comments[0]
        original_id = comment.id
        original_card_id = comment.card_id
        original_user_id = comment.user_id
        original_created_at = comment.created_at
        
        comment_update = CardCommentUpdate(comment="Test")
        
        result = update_comment(db_session, comment.id, comment_update, sample_user.id)
        
        assert result.id == original_id
        assert result.card_id == original_card_id
        assert result.user_id == original_user_id
        assert result.created_at == original_created_at

    def test_update_comment_partial_update(self, db_session, sample_comments, sample_user):
        """Test de mise à jour partielle."""
        comment = sample_comments[0]
        original_comment = comment.comment
        
        # Simuler une mise à jour avec d'autres champs qui ne devraient pas être modifiés
        comment_update = CardCommentUpdate(comment="Texte modifié")
        
        result = update_comment(db_session, comment.id, comment_update, sample_user.id)
        
        assert result.comment == "Texte modifié"
        assert result.card_id == comment.card_id
        assert result.user_id == comment.user_id

    def test_update_comment_unicode_text(self, db_session, sample_comments, sample_user):
        """Test de mise à jour avec texte Unicode."""
        comment = sample_comments[0]
        unicode_text = "Commentaire mis à jour avec caractères spéciaux: éèàçù 🚀 中文"
        
        comment_update = CardCommentUpdate(comment=unicode_text)
        
        result = update_comment(db_session, comment.id, comment_update, sample_user.id)
        
        assert result.comment == unicode_text

    def test_update_comment_integrity_error(self, db_session, sample_comments, sample_user):
        """Test de gestion des erreurs d'intégrité."""
        comment = sample_comments[0]
        comment_update = CardCommentUpdate(comment="Test d'intégrité")
        
        with patch.object(db_session, 'commit', side_effect=IntegrityError("Mock error", {}, None)):
            with pytest.raises(ValueError, match="Erreur d'intégrité lors de la mise à jour du commentaire"):
                update_comment(db_session, comment.id, comment_update, sample_user.id)

    def test_update_comment_reload_error(self, db_session, sample_comments, sample_user):
        """Test de gestion d'erreur lors du rechargement."""
        comment = sample_comments[0]
        comment_update = CardCommentUpdate(comment="Test rechargement")
        
        with patch.object(db_session, 'query') as mock_query:
            mock_query.return_value.options.return_value.filter.return_value.first.return_value = None
            
            with pytest.raises(ValueError):
                update_comment(db_session, comment.id, comment_update, sample_user.id)


class TestDeleteComment:
    """Tests pour la fonction delete_comment."""

    def test_delete_comment_success(self, db_session, sample_comments, sample_user):
        """Test de suppression réussie d'un commentaire."""
        comment = sample_comments[0]
        
        result = delete_comment(db_session, comment.id, sample_user.id)
        
        assert result is True
        
        # Vérifier que le commentaire est marqué comme supprimé
        deleted_comment = db_session.query(CardComment).filter(CardComment.id == comment.id).first()
        assert deleted_comment.is_deleted is True
        
        # Vérifier qu'il n'apparaît plus dans les résultats
        remaining_comments = get_comments_for_card(db_session, comment.card_id)
        assert len(remaining_comments) == 1  # Plus que le deuxième commentaire

    def test_delete_comment_nonexistent(self, db_session, sample_user):
        """Test de suppression d'un commentaire inexistant."""
        result = delete_comment(db_session, 99999, sample_user.id)
        
        assert result is False

    def test_delete_comment_unauthorized_user(self, db_session, sample_comments, sample_user_2):
        """Test de suppression par un utilisateur non autorisé."""
        comment = sample_comments[0]  # Créé par sample_user
        
        with pytest.raises(ValueError, match="Vous ne pouvez supprimer que vos propres commentaires"):
            delete_comment(db_session, comment.id, sample_user_2.id)

    def test_delete_comment_already_deleted(self, db_session, sample_comments, sample_user):
        """Test de suppression d'un commentaire déjà supprimé."""
        comment = sample_comments[2]  # Déjà supprimé par sample_user
        
        result = delete_comment(db_session, comment.id, sample_user.id)
        
        assert result is True
        # Le commentaire reste marqué comme supprimé
        assert comment.is_deleted is True

    def test_delete_comment_integrity_error(self, db_session, sample_comments, sample_user):
        """Test de gestion des erreurs d'intégrité."""
        comment = sample_comments[0]
        
        with patch.object(db_session, 'commit', side_effect=IntegrityError("Mock error", {}, None)):
            with pytest.raises(ValueError, match="Erreur d'intégrité lors de la suppression du commentaire"):
                delete_comment(db_session, comment.id, sample_user.id)

    def test_delete_comment_multiple_deletes(self, db_session, sample_comments, sample_user):
        """Test de suppressions multiples."""
        comment = sample_comments[0]
        
        # Première suppression
        result1 = delete_comment(db_session, comment.id, sample_user.id)
        assert result1 is True
        
        # Deuxième suppression du même commentaire
        result2 = delete_comment(db_session, comment.id, sample_user.id)
        assert result2 is True  # Devrait toujours retourner True

    def test_delete_comment_check_relationships(self, db_session, sample_comments, sample_user):
        """Test que les relations sont préservées après suppression."""
        comment = sample_comments[0]
        original_user = comment.user
        original_card = comment.card
        
        delete_comment(db_session, comment.id, sample_user.id)
        
        # Vérifier que les relations existent toujours
        db_comment = db_session.query(CardComment).filter(CardComment.id == comment.id).first()
        assert db_comment.user == original_user
        assert db_comment.card == original_card


class TestGetCommentById:
    """Tests pour la fonction get_comment_by_id."""

    def test_get_comment_by_id_success(self, db_session, sample_comments):
        """Test de récupération réussie d'un commentaire par ID."""
        comment = sample_comments[0]
        result = get_comment_by_id(db_session, comment.id)
        
        assert result is not None
        assert result.id == comment.id
        assert result.comment == comment.comment
        assert result.user is not None

    def test_get_comment_by_id_deleted(self, db_session, sample_comments):
        """Test de récupération d'un commentaire supprimé."""
        comment = sample_comments[2]  # Commentaire supprimé
        
        result = get_comment_by_id(db_session, comment.id)
        
        assert result is None

    def test_get_comment_by_id_nonexistent(self, db_session):
        """Test de récupération d'un commentaire inexistant."""
        result = get_comment_by_id(db_session, 99999)
        
        assert result is None

    def test_get_comment_by_id_with_user_relationship(self, db_session, sample_comments):
        """Test que la relation user est bien chargée."""
        comment = sample_comments[0]
        result = get_comment_by_id(db_session, comment.id)
        
        assert result is not None
        assert result.user is not None
        assert hasattr(result.user, 'id')
        assert hasattr(result.user, 'display_name')
        assert hasattr(result.user, 'email')


class TestCardCommentIntegration:
    """Tests d'intégration pour le service CardComment."""

    def test_create_update_delete_flow(self, db_session, sample_card, sample_user):
        """Test du flux complet CRUD."""
        # Créer
        comment_data = CardCommentCreate(
            card_id=sample_card.id,
            comment="Commentaire de test"
        )
        created_comment = create_comment(db_session, comment_data, sample_user.id)
        
        # Mettre à jour
        update_data = CardCommentUpdate(comment="Commentaire modifié")
        updated_comment = update_comment(db_session, created_comment.id, update_data, sample_user.id)
        
        assert updated_comment is not None
        assert updated_comment.comment == "Commentaire modifié"
        
        # Supprimer
        delete_result = delete_comment(db_session, created_comment.id, sample_user.id)
        assert delete_result is True
        
        # Vérifier que le commentaire est supprimé
        retrieved_comment = get_comment_by_id(db_session, created_comment.id)
        assert retrieved_comment is None

    def test_multiple_comments_per_card(self, db_session, sample_card, sample_user, sample_user_2):
        """Test de gestion de multiples commentaires par carte."""
        # Créer plusieurs commentaires par différents utilisateurs
        comments_data = [
            (sample_user.id, "Commentaire utilisateur 1"),
            (sample_user_2.id, "Commentaire utilisateur 2"),
            (sample_user.id, "Commentaire utilisateur 3"),
        ]
        
        created_comments = []
        for user_id, text in comments_data:
            comment_data = CardCommentCreate(card_id=sample_card.id, comment=text)
            comment = create_comment(db_session, comment_data, user_id)
            created_comments.append(comment)
        
        # Vérifier que tous les commentaires sont récupérés
        all_comments = get_comments_for_card(db_session, sample_card.id)
        assert len(all_comments) == 3
        
        # Supprimer quelques commentaires
        delete_comment(db_session, created_comments[0].id, sample_user.id)
        delete_comment(db_session, created_comments[1].id, sample_user_2.id)
        
        # Vérifier qu'il ne reste qu'un commentaire
        remaining_comments = get_comments_for_card(db_session, sample_card.id)
        assert len(remaining_comments) == 1
        assert remaining_comments[0].comment == "Commentaire utilisateur 3"

    def test_concurrent_operations(self, db_session, sample_card, sample_user):
        """Test d'opérations concurrentes (simplifié)."""
        # Créer plusieurs commentaires séquentiellement
        comments = []
        for i in range(5):
            comment_data = CardCommentCreate(
                card_id=sample_card.id,
                comment=f"Commentaire {i}"
            )
            comment = create_comment(db_session, comment_data, sample_user.id)
            comments.append(comment)
        
        # Vérifier que tous les commentaires existent
        retrieved_comments = get_comments_for_card(db_session, sample_card.id)
        assert len(retrieved_comments) == 5
        
        # Mettre à jour plusieurs commentaires
        for i, comment in enumerate(comments):
            update_data = CardCommentUpdate(comment=f"Commentaire modifié {i}")
            updated_comment = update_comment(db_session, comment.id, update_data, sample_user.id)
            assert updated_comment.comment == f"Commentaire modifié {i}"

    def test_edge_case_empty_comment(self, db_session, sample_card, sample_user):
        """Test avec commentaire vide (devrait échouer à cause de la validation Pydantic)."""
        with pytest.raises(ValueError):
            CardCommentCreate(card_id=sample_card.id, comment="")

    def test_edge_case_very_long_comment(self, db_session, sample_card, sample_user):
        """Test avec commentaire très long (devrait échouer à cause de la validation Pydantic)."""
        long_comment = "x" * 1001  # Dépasse la limite de 1000
        
        with pytest.raises(ValueError):
            CardCommentCreate(card_id=sample_card.id, comment=long_comment)


class TestCardCommentSecurity:
    """Tests de sécurité pour le service CardComment."""

    def test_sql_injection_prevention(self, db_session, sample_card, sample_user):
        """Test de prévention d'injection SQL."""
        malicious_text = "'; DROP TABLE card_comments; --"
        
        comment_data = CardCommentCreate(
            card_id=sample_card.id,
            comment=malicious_text
        )
        
        # La création devrait fonctionner (le texte est stocké littéralement)
        result = create_comment(db_session, comment_data, sample_user.id)
        assert result.comment == malicious_text
        
        # Vérifier que la table n'a pas été supprimée
        comments = get_comments_for_card(db_session, sample_card.id)
        assert len(comments) > 0

    def test_xss_prevention(self, db_session, sample_card, sample_user):
        """Test de prévention XSS."""
        xss_text = "<script>alert('XSS')</script><img src='x' onerror='alert(1)'>"
        
        comment_data = CardCommentCreate(
            card_id=sample_card.id,
            comment=xss_text
        )
        
        result = create_comment(db_session, comment_data, sample_user.id)
        assert result.comment == xss_text  # Stocké tel quel
        
        # La protection XSS devrait être gérée au niveau du frontend/affichage

    def test_unauthorized_access(self, db_session, sample_comments, sample_user_2):
        """Test d'accès non autorisé aux commentaires d'autres utilisateurs."""
        comment = sample_comments[0]  # Créé par sample_user
        
        # Tenter de modifier le commentaire de quelqu'un d'autre
        update_data = CardCommentUpdate(comment="Tentative de modification non autorisée")
        
        with pytest.raises(ValueError, match="Vous ne pouvez modifier que vos propres commentaires"):
            update_comment(db_session, comment.id, update_data, sample_user_2.id)
        
        # Tenter de supprimer le commentaire de quelqu'un d'autre
        with pytest.raises(ValueError, match="Vous ne pouvez supprimer que vos propres commentaires"):
            delete_comment(db_session, comment.id, sample_user_2.id)

    def test_comment_content_sanitization_storage(self, db_session, sample_card, sample_user):
        """Test que le contenu est stocké tel quel (sanitization au niveau affichage)."""
        dangerous_content = "<script>alert('danger')</script> & <div>HTML content</div>"
        
        comment_data = CardCommentCreate(
            card_id=sample_card.id,
            comment=dangerous_content
        )
        
        result = create_comment(db_session, comment_data, sample_user.id)
        assert result.comment == dangerous_content  # Stocké tel quel

    def test_special_characters_storage(self, db_session, sample_card, sample_user):
        """Test de stockage de caractères spéciaux."""
        special_chars = "éèàçù€£¥©®™•§¶†‡°…‰™œŒšžŠŸŒ"
        
        comment_data = CardCommentCreate(
            card_id=sample_card.id,
            comment=special_chars
        )
        
        result = create_comment(db_session, comment_data, sample_user.id)
        assert result.comment == special_chars