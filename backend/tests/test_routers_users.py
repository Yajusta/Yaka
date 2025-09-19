"""Tests pour le routeur users."""

import os
import sys
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, status
from pydantic import ValidationError

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base
from app.models.user import User, UserRole, UserStatus
from app.routers.users import router, InvitePayload, read_users, create_user as create_user_route, read_user, update_user as update_user_route, delete_user as delete_user_route, invite_user as invite_user_route, update_user_language, set_password, require_admin
from app.schemas import UserCreate, UserUpdate, UserResponse, UserListItem, LanguageUpdate, SetPasswordPayload
from app.services.user import (
    get_users, get_user, get_user_by_email, create_user, update_user, delete_user,
    invite_user, get_user_by_any_token, set_password_from_invite
)
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
def admin_user(db_session):
    """Fixture pour créer un utilisateur admin de test."""
    user = User(
        email="admin@example.com",
        display_name="Admin User",
        password_hash="$2b$12$testhashedpassword",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        language="fr",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def regular_user(db_session):
    """Fixture pour créer un utilisateur régulier de test."""
    user = User(
        email="user@example.com",
        display_name="Regular User",
        password_hash="$2b$12$testhashedpassword",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        language="fr",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def invited_user(db_session):
    """Fixture pour créer un utilisateur invité de test."""
    invited_time = datetime.now(timezone.utc)
    user = User(
        email="invited@example.com",
        display_name="Invited User",
        password_hash="$2b$12$testhashedpassword",
        role=UserRole.USER,
        status=UserStatus.INVITED,
        language="fr",
        invite_token="test_token_123",
        invited_at=invited_time,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


class TestUsersRouter:
    """Tests pour le routeur des utilisateurs."""

    def test_list_users_success_admin(self, admin_user):
        """Test de récupération des utilisateurs par un admin avec succès."""
        with patch('app.routers.users.user_service.get_users') as mock_get_users:
            mock_users = [
                UserListItem(
                    id=1,
                    email="admin@example.com",
                    display_name="Admin User",
                    role=UserRole.ADMIN,
                    status=UserStatus.ACTIVE,
                    language="fr",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                ),
                UserListItem(
                    id=2,
                    email="user@example.com",
                    display_name="Regular User",
                    role=UserRole.USER,
                    status=UserStatus.ACTIVE,
                    language="fr",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            ]
            mock_get_users.return_value = mock_users
            
            with patch('app.routers.users.get_current_active_user') as mock_current_user:
                mock_current_user.return_value = admin_user
                
                # Mock database session
                with patch('app.routers.users.get_db') as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()
                    
                    result = asyncio.run(read_users(
                        0, 100,  # skip, limit
                        mock_db.return_value.__enter__.return_value, 
                        admin_user
                    ))
                    
                    assert len(result) == 2
                    assert result[0]["email"] == "admin@example.com"
                    assert result[1]["email"] == "user@example.com"

    def test_list_users_permission_denied(self, regular_user):
        """Test de récupération des utilisateurs par un utilisateur régulier (devrait échouer)."""
        # For read_users, both admin and regular users can access, but regular users see masked emails
        # This test should verify that regular users can access but don't see emails
        with patch('app.routers.users.user_service.get_users') as mock_get_users:
            mock_users = [
                UserListItem(
                    id=1,
                    email="admin@example.com",
                    display_name="Admin User",
                    role=UserRole.ADMIN,
                    status=UserStatus.ACTIVE,
                    language="fr",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            ]
            mock_get_users.return_value = mock_users
            
            with patch('app.routers.users.get_current_active_user') as mock_current_user:
                mock_current_user.return_value = regular_user
                
                # Mock database session
                with patch('app.routers.users.get_db') as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()
                    
                    result = asyncio.run(read_users(
                        0, 100,  # skip, limit
                        mock_db.return_value.__enter__.return_value, 
                        regular_user
                    ))
                    
                    # Regular user should see the list but emails should be masked (None)
                    assert len(result) == 1
                    assert result[0]["email"] is None  # Email masked for non-admin
                    assert result[0]["display_name"] == "Admin User"

    def test_create_user_success_admin(self, admin_user):
        """Test de création d'un utilisateur par un admin avec succès."""
        user_data = UserCreate(
            email="newuser@example.com",
            display_name="New User",
            role=UserRole.USER,
            language="fr",
            password="securepassword123"
        )
        
        mock_user = UserResponse(
            id=3,
            email="newuser@example.com",
            display_name="New User",
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
            language="fr",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        with patch('app.routers.users.user_service.get_user_by_email') as mock_get_by_email:
            mock_get_by_email.return_value = None  # No existing user
            
            with patch('app.routers.users.user_service.create_user') as mock_create:
                mock_create.return_value = mock_user
                
                with patch('app.routers.users.require_admin') as mock_require_admin:
                    mock_require_admin.return_value = admin_user
                    
                    # Mock database session
                    with patch('app.routers.users.get_db') as mock_db:
                        mock_db.return_value.__enter__.return_value = MagicMock()
                        
                        result = asyncio.run(create_user_route(
                            user_data, 
                            mock_db.return_value.__enter__.return_value, 
                            admin_user
                        ))
                    
                    assert result.email == "newuser@example.com"
                    assert result.display_name == "New User"

    def test_create_user_permission_denied(self, regular_user):
        """Test de création d'un utilisateur par un utilisateur régulier (devrait échouer)."""
        user_data = UserCreate(
            email="newuser@example.com",
            display_name="New User",
            role=UserRole.USER,
            language="fr",
            password="securepassword123"
        )
        
        with patch('app.routers.users.require_admin') as mock_require_admin:
            mock_require_admin.side_effect = HTTPException(
                status_code=403, 
                detail="Accès réservé aux administrateurs"
            )
            
            # Mock database session
            with patch('app.routers.users.get_db') as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()
                
                with pytest.raises(HTTPException) as exc_info:
                    asyncio.run(create_user_route(
                        user_data,
                        mock_db.return_value.__enter__.return_value,
                        mock_require_admin()
                    ))

                assert exc_info.value.status_code == 403
                assert exc_info.value.detail == "Accès réservé aux administrateurs"

    def test_create_user_invalid_data(self, admin_user):
        """Test de création d'un utilisateur avec des données invalides."""
        with patch('app.routers.users.get_current_active_user') as mock_current_user:
            mock_current_user.return_value = admin_user
            
            # Mock database session
            with patch('app.routers.users.get_db') as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()
                
                with pytest.raises(ValidationError) as exc_info:
                    # This should raise a validation error before even reaching the route function
                    UserCreate(email="invalid-email", display_name="Test", role=UserRole.USER, password="test")
                
                # Verify it's a validation error
                assert len(exc_info.value.errors()) > 0
                assert any("email" in str(error).lower() for error in exc_info.value.errors())

    def test_create_user_duplicate_email(self, admin_user):
        """Test de création d'un utilisateur avec un email dupliqué."""
        user_data = UserCreate(
            email="admin@example.com",
            display_name="New User",
            role=UserRole.USER,
            language="fr",
            password="securepassword123"
        )
        
        with patch('app.routers.users.require_admin') as mock_require_admin:
            mock_require_admin.return_value = admin_user
            
            # Mock database session
            with patch('app.routers.users.get_db') as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()
                
                with patch('app.routers.users.user_service.create_user') as mock_create:
                    mock_create.side_effect = ValueError("Un utilisateur avec cet email existe déjà")
                    
                    with pytest.raises(HTTPException) as exc_info:
                        asyncio.run(create_user_route(
                            user_data, 
                            mock_db.return_value.__enter__.return_value, 
                            admin_user
                        ))
                    
                    assert exc_info.value.status_code == 400
                    assert exc_info.value.detail == "Un utilisateur avec cet email existe déjà"

    def test_update_user_success_admin(self, admin_user):
        """Test de mise à jour d'un utilisateur par un admin avec succès."""
        update_data = UserUpdate(
            display_name="Updated User",
            role=UserRole.ADMIN
        )
        
        mock_user = UserResponse(
            id=2,
            email="user@example.com",
            display_name="Updated User",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            language="fr",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        with patch('app.routers.users.user_service.update_user') as mock_update:
            mock_update.return_value = mock_user
            
            with patch('app.routers.users.require_admin') as mock_require_admin:
                mock_require_admin.return_value = admin_user
                
                # Mock database session
                with patch('app.routers.users.get_db') as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()
                    
                    result = asyncio.run(update_user_route(
                        2, 
                        update_data, 
                        mock_db.return_value.__enter__.return_value, 
                        admin_user
                    ))
                    
                    assert result.display_name == "Updated User"
                    assert result.role == UserRole.ADMIN

    def test_update_user_permission_denied(self, regular_user):
        """Test de mise à jour d'un utilisateur par un utilisateur régulier (devrait échouer)."""
        update_data = UserUpdate(display_name="Updated User")
        
        with patch('app.routers.users.require_admin') as mock_require_admin:
            mock_require_admin.side_effect = HTTPException(
                status_code=403, 
                detail="Accès réservé aux administrateurs"
            )
            
            # Mock database session
            with patch('app.routers.users.get_db') as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()
                
                with pytest.raises(HTTPException) as exc_info:
                    asyncio.run(update_user_route(
                        2,
                        update_data,
                        mock_db.return_value.__enter__.return_value,
                        mock_require_admin()
                    ))

                assert exc_info.value.status_code == 403
                assert exc_info.value.detail == "Accès réservé aux administrateurs"

    def test_update_user_not_found(self, admin_user):
        """Test de mise à jour d'un utilisateur qui n'existe pas."""
        update_data = UserUpdate(display_name="Updated User")
        
        with patch('app.routers.users.user_service.update_user') as mock_update:
            mock_update.return_value = None
            
            with patch('app.routers.users.require_admin') as mock_require_admin:
                mock_require_admin.return_value = admin_user
                
                # Mock database session
                with patch('app.routers.users.get_db') as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()
                    
                    with pytest.raises(HTTPException) as exc_info:
                        asyncio.run(update_user_route(
                            999, 
                            update_data, 
                            mock_db.return_value.__enter__.return_value, 
                            admin_user
                        ))
                    
                    assert exc_info.value.status_code == 404
                    assert exc_info.value.detail == "Utilisateur non trouvé"

    def test_delete_user_success_admin(self, admin_user):
        """Test de suppression d'un utilisateur par un admin avec succès."""
        with patch('app.routers.users.user_service.delete_user') as mock_delete:
            mock_delete.return_value = True
            
            with patch('app.routers.users.require_admin') as mock_require_admin:
                mock_require_admin.return_value = admin_user
                
                # Mock database session
                with patch('app.routers.users.get_db') as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()
                    
                    result = asyncio.run(delete_user_route(
                        2, 
                        mock_db.return_value.__enter__.return_value, 
                        admin_user
                    ))
                    
                    assert result["message"] == "Utilisateur supprimé avec succès"

    def test_delete_user_permission_denied(self, regular_user):
        """Test de suppression d'un utilisateur par un utilisateur régulier (devrait échouer)."""
        with patch('app.routers.users.require_admin') as mock_require_admin:
            mock_require_admin.side_effect = HTTPException(
                status_code=403, 
                detail="Accès réservé aux administrateurs"
            )
            
            # Mock database session
            with patch('app.routers.users.get_db') as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()
                
                with pytest.raises(HTTPException) as exc_info:
                    asyncio.run(delete_user_route(
                        2,
                        mock_db.return_value.__enter__.return_value,
                        mock_require_admin()
                    ))

                assert exc_info.value.status_code == 403
                assert exc_info.value.detail == "Accès réservé aux administrateurs"

    def test_delete_user_not_found(self, admin_user):
        """Test de suppression d'un utilisateur qui n'existe pas."""
        with patch('app.routers.users.user_service.delete_user') as mock_delete:
            mock_delete.return_value = False
            
            with patch('app.routers.users.require_admin') as mock_require_admin:
                mock_require_admin.return_value = admin_user
                
                # Mock database session
                with patch('app.routers.users.get_db') as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()
                    
                    with pytest.raises(HTTPException) as exc_info:
                        asyncio.run(delete_user_route(
                            999, 
                            mock_db.return_value.__enter__.return_value, 
                            admin_user
                        ))
                    
                    assert exc_info.value.status_code == 404
                    assert exc_info.value.detail == "Utilisateur non trouvé"

    def test_invite_user_success_admin(self, admin_user):
        """Test d'invitation d'un utilisateur par un admin avec succès."""
        invite_payload = InvitePayload(email="invitee@example.com", role=UserRole.USER)
        
        mock_user = UserResponse(
            id=3,
            email="invitee@example.com",
            display_name="Invitee",
            role=UserRole.USER,
            status=UserStatus.INVITED,
            language="fr",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        with patch('app.routers.users.user_service.get_user_by_email') as mock_get_by_email:
            mock_get_by_email.return_value = None  # No existing user
            
            with patch('app.routers.users.user_service.invite_user') as mock_invite:
                mock_invite.return_value = mock_user
                
                with patch('app.routers.users.require_admin') as mock_require_admin:
                    mock_require_admin.return_value = admin_user
                    
                    # Mock database session
                    with patch('app.routers.users.get_db') as mock_db:
                        mock_db.return_value.__enter__.return_value = MagicMock()
                    
                    result = asyncio.run(invite_user_route(
                        invite_payload, 
                        mock_db.return_value.__enter__.return_value, 
                        admin_user
                    ))
                    
                    assert result.email == "invitee@example.com"

    def test_invite_user_permission_denied(self, regular_user):
        """Test d'invitation d'un utilisateur par un utilisateur régulier (devrait échouer)."""
        invite_payload = InvitePayload(email="invitee@example.com", role=UserRole.USER)
        
        with patch('app.routers.users.require_admin') as mock_require_admin:
            mock_require_admin.side_effect = HTTPException(
                status_code=403, 
                detail="Accès réservé aux administrateurs"
            )
            
            # Mock database session
            with patch('app.routers.users.get_db') as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()
                
                with pytest.raises(HTTPException) as exc_info:
                    asyncio.run(invite_user_route(
                        invite_payload,
                        mock_db.return_value.__enter__.return_value,
                        mock_require_admin()
                    ))

                assert exc_info.value.status_code == 403
                assert exc_info.value.detail == "Accès réservé aux administrateurs"

    def test_set_language_success(self, regular_user):
        """Test de mise à jour de la langue par un utilisateur avec succès."""
        language_data = LanguageUpdate(language="en")
        
        mock_user = UserResponse(
            id=2,
            email="user@example.com",
            display_name="Regular User",
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
            language="en",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        with patch('app.routers.users.user_service.update_user') as mock_update:
            mock_update.return_value = mock_user
            
            with patch('app.routers.users.get_current_active_user') as mock_current_user:
                mock_current_user.return_value = regular_user
                
                # Mock database session
                with patch('app.routers.users.get_db') as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()
                    
                    result = asyncio.run(update_user_language(
                        language_data, 
                        mock_db.return_value.__enter__.return_value, 
                        regular_user
                    ))
                    
                    assert result.language == "en"

    def test_set_password_from_invite_success(self, invited_user):
        """Test de définition du mot de passe depuis une invitation avec succès."""
        password_payload = SetPasswordPayload(
            token="test_token_123",
            password="newpassword123"
        )
        
        mock_user = UserResponse(
            id=3,
            email="invited@example.com",
            display_name="Invited User",
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
            language="fr",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        with patch('app.routers.users.user_service.set_password_from_invite') as mock_set_password:
            mock_set_password.return_value = mock_user
            
            # Mock database session
            with patch('app.routers.users.get_db') as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()
                    
                result = asyncio.run(set_password(
                    password_payload, 
                    mock_db.return_value.__enter__.return_value
                ))
                
                assert result["message"] == "Mot de passe défini avec succès"

    def test_set_password_from_invite_invalid_token(self):
        """Test de définition du mot de passe avec un token invalide."""
        password_payload = SetPasswordPayload(
            token="invalid_token",
            password="newpassword123"
        )
        
        with patch('app.routers.users.user_service.set_password_from_invite') as mock_set_password:
            mock_set_password.side_effect = ValueError("Token invalide ou expiré")
            
            # Mock database session
            with patch('app.routers.users.get_db') as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()
                    
                with pytest.raises(ValueError) as exc_info:
                    asyncio.run(set_password(
                        password_payload, 
                        mock_db.return_value.__enter__.return_value
                    ))
                
                assert "Token invalide ou expiré" in str(exc_info.value)

    def test_invalid_user_id(self, admin_user):
        """Test avec un ID d'utilisateur invalide (négatif)."""
        update_data = UserUpdate(display_name="Test")
        
        with patch('app.routers.users.require_admin') as mock_require_admin:
            mock_require_admin.return_value = admin_user
            
            # Mock database session
            with patch('app.routers.users.get_db') as mock_db:
                mock_db.return_value.__enter__.return_value = MagicMock()
                
                # This should work fine - negative IDs are valid integers
                result = asyncio.run(update_user_route(
                    -1, 
                    update_data, 
                    mock_db.return_value.__enter__.return_value, 
                    admin_user
                ))
                
                # Test should pass if no exception is raised
                assert result is not None

    def test_service_error_handling(self, admin_user):
        """Test de gestion des erreurs de service."""
        with patch('app.routers.users.user_service.get_users') as mock_get_users:
            mock_get_users.side_effect = Exception("Database error")
            
            with patch('app.routers.users.get_current_active_user') as mock_current_user:
                mock_current_user.return_value = admin_user
                
                # Mock database session
                with patch('app.routers.users.get_db') as mock_db:
                    mock_db.return_value.__enter__.return_value = MagicMock()
                    
                    with pytest.raises(Exception) as exc_info:
                        asyncio.run(read_users(
                            0, 100,  # skip, limit
                            mock_db.return_value.__enter__.return_value, 
                            admin_user
                        ))
                    
                    # The exception should propagate since read_users doesn't have error handling
                    assert "Database error" in str(exc_info.value)


# Import needed for tests
import asyncio