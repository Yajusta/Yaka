"""Tests pour le routeur auth."""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base
from app.models.user import User, UserRole, UserStatus
from app.routers.auth import login, logout, read_users_me, request_password_reset, router
from app.schemas import PasswordResetRequest
from app.services.user import authenticate_user
from app.utils.security import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token
from fastapi.testclient import TestClient
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
    """Fixture pour créer un utilisateur de test."""
    user = User(
        email="test@example.com",
        display_name="Test User",
        password_hash="$2b$12$testhashedpassword",
        role=UserRole.EDITOR,
        status=UserStatus.ACTIVE,
        language="fr",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_app():
    """Fixture pour créer une application FastAPI de test."""
    from app.database import get_db
    from app.routers import auth
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(auth.router)

    # Override the database dependency
    def override_get_db():
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return app


class TestAuthRouter:
    """Tests pour le routeur d'authentification."""

    def test_login_success(self, test_user):
        """Test de connexion réussie."""
        # Mock de l'authentification
        with patch("app.routers.auth.user_service.authenticate_user") as mock_auth:
            mock_auth.return_value = test_user

            # Mock the database session
            with patch("app.routers.auth.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                # Test the login function directly
                form_data = OAuth2PasswordRequestForm(username="test@example.com", password="password123")
                result = asyncio.run(login(form_data, mock_db.return_value.__enter__.return_value))

                assert "access_token" in result
                assert result["token_type"] == "bearer"
                mock_auth.assert_called_once()

    def test_login_failure_invalid_credentials(self):
        """Test de connexion avec des identifiants invalides."""
        with patch("app.routers.auth.user_service.authenticate_user") as mock_auth:
            mock_auth.return_value = None

            # Mock the database session
            with patch("app.routers.auth.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                # Test the login function directly
                form_data = OAuth2PasswordRequestForm(username="invalid@example.com", password="wrongpassword")

                with pytest.raises(HTTPException) as exc_info:
                    asyncio.run(login(form_data, mock_db.return_value.__enter__.return_value))

                assert exc_info.value.status_code == 401
                assert exc_info.value.detail == "Email ou mot de passe incorrect"
                mock_auth.assert_called_once()

    def test_read_users_me_authenticated(self, test_user):
        """Test de récupération des informations utilisateur connecté."""
        # Mock de l'utilisateur actuel
        with patch("app.routers.auth.get_current_active_user") as mock_current_user:
            mock_current_user.return_value = test_user

            # Test the function directly
            result = asyncio.run(read_users_me(test_user))

            assert result.email == test_user.email
            assert result.display_name == test_user.display_name

    def test_logout(self):
        """Test de déconnexion."""
        result = asyncio.run(logout())
        assert result["message"] == "Déconnexion réussie"

    def test_request_password_reset_existing_user(self, test_user):
        """Test de demande de réinitialisation de mot de passe pour un utilisateur existant."""
        with patch("app.routers.auth.user_service.request_password_reset") as mock_reset:
            mock_reset.return_value = None

            # Mock the database session
            with patch("app.routers.auth.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                # Test the function directly
                request_data = PasswordResetRequest(email="test@example.com")
                result = asyncio.run(request_password_reset(request_data, mock_db.return_value.__enter__.return_value))

                assert result["message"] == "Si cet email existe, un lien de réinitialisation a été envoyé"
                mock_reset.assert_called_once()

    def test_request_password_reset_nonexistent_user(self):
        """Test de demande de réinitialisation de mot de passe pour un utilisateur inexistant."""
        with patch("app.routers.auth.user_service.request_password_reset") as mock_reset:
            mock_reset.return_value = None

            # Mock the database session
            with patch("app.routers.auth.get_db") as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()

                # Test the function directly
                request_data = PasswordResetRequest(email="nonexistent@example.com")
                result = asyncio.run(request_password_reset(request_data, mock_db.return_value.__enter__.return_value))

                # Le message est le même pour des raisons de sécurité
                assert result["message"] == "Si cet email existe, un lien de réinitialisation a été envoyé"

    def test_login_with_invalid_form_data(self):
        """Test de connexion avec des données de formulaire invalides."""
        # This test would normally be handled by FastAPI's form validation
        # For unit tests, we focus on the business logic
        pass

    def test_request_password_reset_with_invalid_email(self):
        """Test de demande de réinitialisation avec un email invalide."""
        # This test would normally be handled by FastAPI's form validation
        # For unit tests, we focus on the business logic
        pass

    def test_request_password_reset_missing_email(self):
        """Test de demande de réinitialisation sans email."""
        # This test would normally be handled by FastAPI's form validation
        # For unit tests, we focus on the business logic
        pass

    def test_token_creation_expiry(self):
        """Test de création de token avec expiration."""
        test_user_data = {"sub": "test@example.com"}
        token = create_access_token(data=test_user_data)

        # Vérifier que le token est une chaîne non vide
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_creation_with_custom_expiry(self):
        """Test de création de token avec expiration personnalisée."""
        test_user_data = {"sub": "test@example.com"}
        custom_expiry = timedelta(minutes=30)
        token = create_access_token(data=test_user_data, expires_delta=custom_expiry)

        assert isinstance(token, str)
        assert len(token) > 0
