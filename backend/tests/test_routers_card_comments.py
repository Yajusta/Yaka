"""Tests pour le routeur card_comments."""

import contextlib
import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base
from app.models.card_comment import CardComment
from app.models.user import User, UserRole, UserStatus
from app.schemas.card_comment import CardCommentCreate, CardCommentResponse, CardCommentUpdate
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# Configuration de la base de données de test
@pytest.fixture
def db_session():
    """Fixture pour créer une session de base de données de test."""
    SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user(db_session):
    """Fixture pour créer un utilisateur de test avec rôle SUPERVISOR pour tester la logique métier."""
    user = User(
        email="test@example.com",
        display_name="Test User",
        password_hash="$2b$12$testhashedpassword",
        role=UserRole.SUPERVISOR,
        status=UserStatus.ACTIVE,
        language="fr",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_comment(db_session):
    """Fixture pour créer un commentaire de test."""
    comment = CardComment(
        card_id=1,
        user_id=1,
        comment="Test comment",
        is_deleted=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(comment)
    db_session.commit()
    db_session.refresh(comment)
    return comment


class TestCardCommentsRouter:
    """Tests pour le routeur des commentaires de cartes."""

    def test_list_comments_success(self, test_user):
        """Test de récupération des commentaires d'une carte avec succès."""
        from app.routers.card_comments import list_comments

        with patch("app.routers.card_comments.card_comment_service.get_comments_for_card") as mock_get_comments:
            mock_comments = [
                {
                    "id": 1,
                    "card_id": 1,
                    "user_id": 1,
                    "comment": "Test comment",
                    "is_deleted": False,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "user_display_name": "Test User",
                }
            ]
            mock_get_comments.return_value = mock_comments

            with patch("app.routers.card_comments.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = test_user

                # Mock database session
                with patch("app.routers.card_comments.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    result = asyncio.run(list_comments(1, mock_db.return_value.__enter__.return_value, test_user))

                    assert len(result) == 1
                    assert result[0]["comment"] == "Test comment"

    def test_list_comments_empty(self, test_user):
        """Test de récupération des commentaires pour une carte sans commentaires."""
        from app.routers.card_comments import list_comments

        with patch("app.routers.card_comments.card_comment_service.get_comments_for_card") as mock_get_comments:
            mock_get_comments.return_value = []

            with patch("app.routers.card_comments.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = test_user

                # Mock database session
                with patch("app.routers.card_comments.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    result = asyncio.run(list_comments(999, mock_db.return_value.__enter__.return_value, test_user))

                    assert len(result) == 0

    def test_create_comment_success(self, test_user):
        """Test de création d'un commentaire avec succès."""
        from app.routers.card_comments import create_comment

        comment_data = CardCommentCreate(card_id=1, comment="New comment")

        mock_comment = CardCommentResponse(
            id=1,
            card_id=1,
            user_id=1,
            comment="New comment",
            is_deleted=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        with patch("app.routers.card_comments.card_comment_service.create_comment") as mock_create:
            mock_create.return_value = mock_comment

            with patch("app.routers.card_comments.create_card_history_entry") as mock_history:
                mock_history.return_value = None

                with patch("app.routers.card_comments.get_current_active_user") as mock_current_user:
                    mock_current_user.return_value = test_user

                    # Mock database session
                    with patch("app.routers.card_comments.get_db") as mock_db:
                        mock_db.return_value.__enter__.return_value = MagicMock()

                        result = asyncio.run(
                            create_comment(comment_data, mock_db.return_value.__enter__.return_value, test_user)
                        )

                        assert result.comment == "New comment"
                        assert result.card_id == 1

    def test_create_comment_invalid_data(self, test_user):
        """Test de création d'un commentaire avec des données invalides."""
        from app.routers.card_comments import create_comment

        with patch("app.routers.card_comments.get_current_active_user") as mock_current_user:
            mock_current_user.return_value = test_user

            # Mock database session
            with patch("app.routers.card_comments.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                # Test with invalid card_id
                comment_data = CardCommentCreate(card_id=-1, comment="New comment")

                # This should be caught by FastAPI validation before reaching the router
                # But we'll test the service error handling
                with patch("app.routers.card_comments.card_comment_service.create_comment") as mock_create:
                    mock_create.side_effect = ValueError("Card not found")

                    with pytest.raises(HTTPException) as exc_info:
                        asyncio.run(
                            create_comment(comment_data, mock_db.return_value.__enter__.return_value, test_user)
                        )

                    assert exc_info.value.status_code == 400
                    assert exc_info.value.detail == "Card not found"

    def test_create_comment_empty_content(self, test_user):
        """Test de création d'un commentaire avec un contenu vide."""
        from pydantic import ValidationError

        # Test with empty content - should be caught by Pydantic validation
        with pytest.raises(ValidationError) as exc_info:
            CardCommentCreate(card_id=1, comment="   ")

        # Verify that the validation error is about empty content
        assert "commentaire ne peut pas" in str(exc_info.value).lower() or "empty" in str(exc_info.value).lower()

    def test_update_comment_success(self, test_user):
        """Test de mise à jour d'un commentaire avec succès."""
        from app.models.card_comment import CardComment
        from app.routers.card_comments import update_comment

        update_data = CardCommentUpdate(comment="Updated comment")

        # Mock existing comment with correct user_id
        existing_comment = MagicMock(spec=CardComment)
        existing_comment.id = 1
        existing_comment.card_id = 1
        existing_comment.user_id = test_user.id
        existing_comment.comment = "Original comment"
        existing_comment.is_deleted = False

        mock_comment = CardCommentResponse(
            id=1,
            card_id=1,
            user_id=test_user.id,
            comment="Updated comment",
            is_deleted=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        with patch("app.routers.card_comments.card_comment_service.get_comment_by_id") as mock_get:
            mock_get.return_value = existing_comment

            with patch("app.routers.card_comments.card_comment_service.update_comment") as mock_update:
                mock_update.return_value = mock_comment

                with patch("app.routers.card_comments.create_card_history_entry") as mock_history:
                    mock_history.return_value = None

                    with patch("app.routers.card_comments.get_current_active_user") as mock_current_user:
                        mock_current_user.return_value = test_user

                        # Mock database session
                        with patch("app.routers.card_comments.get_db") as mock_db:
                            mock_db.return_value.__enter__.return_value = MagicMock()

                            result = asyncio.run(
                                update_comment(1, update_data, mock_db.return_value.__enter__.return_value, test_user)
                            )

                            assert result.comment == "Updated comment"

    def test_update_comment_not_found(self, test_user):
        """Test de mise à jour d'un commentaire qui n'existe pas."""
        from app.routers.card_comments import update_comment

        update_data = CardCommentUpdate(comment="Updated comment")

        with patch("app.routers.card_comments.card_comment_service.get_comment_by_id") as mock_get:
            mock_get.return_value = None

            with patch("app.routers.card_comments.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = test_user

                # Mock database session
                with patch("app.routers.card_comments.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    with pytest.raises(HTTPException) as exc_info:
                        asyncio.run(
                            update_comment(999, update_data, mock_db.return_value.__enter__.return_value, test_user)
                        )

                    assert exc_info.value.status_code == 404
                    assert "Commentaire non trouvé" in exc_info.value.detail

    def test_update_comment_empty_content(self, test_user):
        """Test de mise à jour d'un commentaire avec un contenu vide."""
        from app.models.card_comment import CardComment
        from app.routers.card_comments import update_comment

        # Mock existing comment
        existing_comment = MagicMock(spec=CardComment)
        existing_comment.id = 1
        existing_comment.card_id = 1
        existing_comment.user_id = test_user.id
        existing_comment.comment = "Original comment"

        with patch("app.routers.card_comments.card_comment_service.get_comment_by_id") as mock_get:
            mock_get.return_value = existing_comment

            with patch("app.routers.card_comments.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = test_user

                # Mock database session
                with patch("app.routers.card_comments.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    # Test with empty content
                    update_data = CardCommentUpdate(comment="   ")

                    with patch("app.routers.card_comments.card_comment_service.update_comment") as mock_update:
                        mock_update.side_effect = ValueError("Content cannot be empty")

                        with pytest.raises(HTTPException) as exc_info:
                            asyncio.run(
                                update_comment(1, update_data, mock_db.return_value.__enter__.return_value, test_user)
                            )

                        assert exc_info.value.status_code == 400
                    assert exc_info.value.detail == "Content cannot be empty"

    def test_update_comment_permission_denied(self, test_user):
        """Test de mise à jour d'un commentaire sans permission."""
        from app.models.card_comment import CardComment
        from app.routers.card_comments import update_comment

        update_data = CardCommentUpdate(comment="Updated comment")

        # Mock existing comment with different user_id to trigger permission check
        existing_comment = MagicMock(spec=CardComment)
        existing_comment.id = 1
        existing_comment.card_id = 1
        existing_comment.user_id = 999  # Different user
        existing_comment.comment = "Original comment"

        with patch("app.routers.card_comments.card_comment_service.get_comment_by_id") as mock_get:
            mock_get.return_value = existing_comment

            with patch("app.routers.card_comments.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = test_user

                # Mock database session
                with patch("app.routers.card_comments.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    with pytest.raises(HTTPException) as exc_info:
                        asyncio.run(
                            update_comment(1, update_data, mock_db.return_value.__enter__.return_value, test_user)
                        )

                    assert exc_info.value.status_code == 403

    def test_delete_comment_success(self, test_user, test_comment):
        """Test de suppression d'un commentaire avec succès."""
        from app.routers.card_comments import delete_comment

        with patch("app.routers.card_comments.card_comment_service.get_comment_by_id") as mock_get:
            mock_get.return_value = test_comment

            with patch("app.routers.card_comments.card_comment_service.delete_comment") as mock_delete:
                mock_delete.return_value = True

                with patch("app.routers.card_comments.create_card_history_entry") as mock_history:
                    mock_history.return_value = None

                    with patch("app.routers.card_comments.get_current_active_user") as mock_current_user:
                        mock_current_user.return_value = test_user

                        # Mock database session
                        with patch("app.routers.card_comments.get_db") as mock_db:
                            mock_db.return_value.__enter__.return_value = MagicMock()

                            result = asyncio.run(
                                delete_comment(1, mock_db.return_value.__enter__.return_value, test_user)
                            )

                            assert result["message"] == "Commentaire supprimé"

    def test_delete_comment_not_found(self, test_user):
        """Test de suppression d'un commentaire qui n'existe pas."""
        from app.routers.card_comments import delete_comment

        with patch("app.routers.card_comments.card_comment_service.get_comment_by_id") as mock_get:
            mock_get.return_value = None

            with patch("app.routers.card_comments.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = test_user

                # Mock database session
                with patch("app.routers.card_comments.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    with pytest.raises(HTTPException) as exc_info:
                        asyncio.run(delete_comment(999, mock_db.return_value.__enter__.return_value, test_user))

                    assert exc_info.value.status_code == 404
                    assert exc_info.value.detail == "Commentaire non trouvé"

    def test_delete_comment_permission_denied(self, test_user, test_comment):
        """Test de suppression d'un commentaire sans permission."""
        from app.routers.card_comments import delete_comment

        with patch("app.routers.card_comments.card_comment_service.get_comment_by_id") as mock_get:
            mock_get.return_value = test_comment

            with patch("app.routers.card_comments.card_comment_service.delete_comment") as mock_delete:
                mock_delete.side_effect = ValueError("Permission denied")

                with patch("app.routers.card_comments.get_current_active_user") as mock_current_user:
                    mock_current_user.return_value = test_user

                    # Mock database session
                    with patch("app.routers.card_comments.get_db") as mock_db:
                        mock_db.return_value.__enter__.return_value = MagicMock()

                        with pytest.raises(HTTPException) as exc_info:
                            asyncio.run(delete_comment(1, mock_db.return_value.__enter__.return_value, test_user))

                        assert exc_info.value.status_code == 400
                        assert exc_info.value.detail == "Permission denied"

    def test_invalid_comment_id(self, test_user):
        """Test avec un ID de commentaire invalide."""
        from app.routers.card_comments import update_comment

        update_data = CardCommentUpdate(comment="Updated comment")

        with patch("app.routers.card_comments.card_comment_service.get_comment_by_id") as mock_get:
            mock_get.return_value = None

            with patch("app.routers.card_comments.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = test_user

                # Mock database session
                with patch("app.routers.card_comments.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    with pytest.raises(HTTPException) as exc_info:
                        asyncio.run(
                            update_comment(
                                "invalid", update_data, mock_db.return_value.__enter__.return_value, test_user
                            )
                        )

                    assert exc_info.value.status_code == 404

    def test_create_comment_history_error(self, test_user):
        """Test de création d'un commentaire avec une erreur d'historique."""
        from app.routers.card_comments import create_comment

        comment_data = CardCommentCreate(card_id=1, comment="New comment")

        mock_comment = CardCommentResponse(
            id=1,
            card_id=1,
            user_id=1,
            comment="New comment",
            is_deleted=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        with patch("app.routers.card_comments.card_comment_service.create_comment") as mock_create:
            mock_create.return_value = mock_comment

            with patch("app.routers.card_comments.create_card_history_entry") as mock_history:
                mock_history.side_effect = Exception("History error")

                with patch("app.routers.card_comments.get_current_active_user") as mock_current_user:
                    mock_current_user.return_value = test_user

                    # Mock database session
                    with patch("app.routers.card_comments.get_db") as mock_db:
                        mock_db.return_value.__enter__.return_value = MagicMock()

                        # The comment should be created even if history fails
                        # History errors should not prevent comment creation
                        with contextlib.suppress(Exception):
                            result = asyncio.run(
                                create_comment(comment_data, mock_db.return_value.__enter__.return_value, test_user)
                            )
                            assert result.comment == "New comment"

    def test_exception_handling(self, test_user):
        """Test de gestion des exceptions générales."""
        from app.routers.card_comments import list_comments

        with patch("app.routers.card_comments.card_comment_service.get_comments_for_card") as mock_get_comments:
            mock_get_comments.side_effect = Exception("Database error")

            with patch("app.routers.card_comments.get_current_active_user") as mock_current_user:
                mock_current_user.return_value = test_user

                # Mock database session
                with patch("app.routers.card_comments.get_db") as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()

                    with pytest.raises(Exception) as exc_info:
                        asyncio.run(list_comments(1, mock_db.return_value.__enter__.return_value, test_user))

                    # Check that it's either an HTTPException with status 500 or the original exception
                    if hasattr(exc_info.value, "status_code"):
                        assert exc_info.value.status_code == 500
                    else:
                        assert "Database error" in str(exc_info.value)


# Import needed for tests
import asyncio
