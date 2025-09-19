"""Tests pour le service User."""

import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base
from app.models.user import User, UserRole, UserStatus
from app.schemas.user import UserCreate, UserUpdate
from app.services.user import (
    authenticate_user,
    create_admin_user,
    create_user,
    delete_user,
    get_system_timezone_datetime,
    get_user,
    get_user_by_any_token,
    get_user_by_email,
    get_user_by_invite_token,
    get_user_by_reset_token,
    get_users,
    invite_user,
    request_password_reset,
    set_password_from_invite,
    update_user,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# Configuration de la base de données de test
@pytest.fixture
def db_session():
    """Fixture pour créer une session de base de données de test."""
    # Utiliser une base de données en mémoire pour éviter les conflits
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
def sample_user_data():
    """Fixture pour fournir des données utilisateur de test."""
    return {
        "email": "test@example.com",
        "password": "password123",
        "display_name": "Test User",
        "role": UserRole.USER,
        "language": "fr",
    }


@pytest.fixture
def sample_users(db_session, sample_user_data):
    """Fixture pour créer des utilisateurs de test."""
    users = []

    # Créer un utilisateur actif
    user1_data = UserCreate(**sample_user_data)
    user1 = create_user(db_session, user1_data)
    users.append(user1)

    # Créer un utilisateur invité
    user2 = invite_user(db_session, email="invited@example.com", display_name="Invited User", role=UserRole.USER)
    users.append(user2)

    # Créer un administrateur
    admin_data = UserCreate(
        email="admin@example.com",
        password="admin123",
        display_name="Admin User",
        role=UserRole.ADMIN,
        language="en",
    )
    admin = create_user(db_session, admin_data)
    users.append(admin)

    return users


@pytest.fixture(autouse=True)
def mock_email_service():
    """Fixture pour mocker le service email (autouse pour s'appliquer à tous les tests)."""
    with patch("app.services.user.email_service.send_invitation") as mock_send_invitation, patch(
        "app.services.user.email_service.send_password_reset"
    ) as mock_send_reset:
        # Créer un objet mock qui contient les deux fonctions
        mock = MagicMock()
        mock.send_invitation = mock_send_invitation
        mock.send_password_reset = mock_send_reset
        yield mock


class TestGetSystemTimezoneDatetime:
    """Tests pour la fonction get_system_timezone_datetime."""

    def test_get_system_timezone_datetime(self):
        """Test de récupération de la date et heure actuelle."""
        result = get_system_timezone_datetime()
        assert isinstance(result, datetime)
        assert result.tzinfo is not None


class TestGetUser:
    """Tests pour la fonction get_user."""

    def test_get_existing_user(self, db_session, sample_users):
        """Test de récupération d'un utilisateur existant."""
        user = sample_users[0]
        result = get_user(db_session, user.id)

        assert result is not None
        assert result.id == user.id
        assert result.email == user.email
        assert result.display_name == user.display_name

    def test_get_nonexistent_user(self, db_session):
        """Test de récupération d'un utilisateur qui n'existe pas."""
        result = get_user(db_session, 999999)
        assert result is None

    def test_get_deleted_user(self, db_session, sample_users):
        """Test de récupération d'un utilisateur supprimé."""
        user = sample_users[0]
        user.status = UserStatus.DELETED
        db_session.commit()

        result = get_user(db_session, user.id)
        assert result is None


class TestGetUserByEmail:
    """Tests pour la fonction get_user_by_email."""

    def test_get_user_by_existing_email(self, db_session, sample_users):
        """Test de récupération d'un utilisateur par email existant."""
        user = sample_users[0]
        result = get_user_by_email(db_session, user.email)

        assert result is not None
        assert result.id == user.id
        assert result.email == user.email

    def test_get_user_by_nonexistent_email(self, db_session):
        """Test de récupération d'un utilisateur par email qui n'existe pas."""
        result = get_user_by_email(db_session, "nonexistent@example.com")
        assert result is None

    def test_get_user_by_email_case_insensitive(self, db_session, sample_users):
        """Test de récupération d'un utilisateur par email insensible à la casse."""
        user = sample_users[0]
        result = get_user_by_email(db_session, user.email.upper())

        assert result is not None
        assert result.id == user.id
        assert result.email == user.email

    def test_get_user_by_email_trims_whitespace(self, db_session, sample_users):
        """Les espaces superflus autour de l'adresse ne doivent pas affecter la recherche."""
        user = sample_users[0]
        result = get_user_by_email(db_session, f"  {user.email}  ")

        assert result is not None
        assert result.id == user.id

    def test_get_deleted_user_by_email(self, db_session, sample_users):
        """Test de récupération d'un utilisateur supprimé par email."""
        user = sample_users[0]
        user.status = UserStatus.DELETED
        db_session.commit()

        result = get_user_by_email(db_session, user.email)
        assert result is None


class TestGetUsers:
    """Tests pour la fonction get_users."""

    def test_get_all_users(self, db_session, sample_users):
        """Test de récupération de tous les utilisateurs."""
        users = get_users(db_session)
        assert len(users) == 3

        emails = [u.email for u in users]
        assert "test@example.com" in emails
        assert "invited@example.com" in emails
        assert "admin@example.com" in emails

    def test_get_users_with_skip_and_limit(self, db_session, sample_users):
        """Test de récupération d'utilisateurs avec pagination."""
        users = get_users(db_session, skip=1, limit=1)
        assert len(users) == 1

    def test_get_users_excludes_deleted(self, db_session, sample_users):
        """Test que les utilisateurs supprimés ne sont pas retournés."""
        user = sample_users[0]
        user.status = UserStatus.DELETED
        db_session.commit()

        users = get_users(db_session)
        assert len(users) == 2

        emails = [u.email for u in users]
        assert user.email not in emails

    def test_get_users_empty_database(self, db_session):
        """Test de récupération d'utilisateurs d'une base vide."""
        users = get_users(db_session)
        assert len(users) == 0


class TestCreateUser:
    """Tests pour la fonction create_user."""

    def test_create_user_successfully(self, db_session, sample_user_data):
        """Test de création réussie d'un utilisateur."""
        user_data = UserCreate(**sample_user_data)
        user = create_user(db_session, user_data)

    def test_create_user_normalizes_email(self, db_session, sample_user_data):
        """L'adresse email doit être stockée en minuscules."""
        payload = sample_user_data.copy()
        payload["email"] = "MixedCaseUser@Example.Com"
        user_data = UserCreate(**payload)
        user = create_user(db_session, user_data)

        assert user.email == "mixedcaseuser@example.com"
        assert user.id is not None
        assert user.email == user_data.email
        assert user.display_name == user_data.display_name
        assert user.role == user_data.role
        assert user.language == user_data.language
        assert user.status == UserStatus.ACTIVE
        assert user.password_hash is not None
        assert user.password_hash != user_data.password  # Le mot de passe doit être haché

    def test_create_user_without_language(self, db_session):
        """Test de création d'un utilisateur sans spécifier la langue."""
        user_data = UserCreate(
            email="test2@example.com",
            password="password123",
            display_name="Test User 2",
            role=UserRole.USER,
        )
        user = create_user(db_session, user_data)

        assert user.language == "fr"  # Valeur par défaut

    def test_create_user_with_admin_role(self, db_session):
        """Test de création d'un utilisateur avec le rôle admin."""
        user_data = UserCreate(
            email="admin2@example.com",
            password="admin123",
            display_name="Admin User 2",
            role=UserRole.ADMIN,
        )
        user = create_user(db_session, user_data)

        assert user.role == UserRole.ADMIN

    def test_create_user_duplicate_email(self, db_session, sample_users):
        """Test de création d'un utilisateur avec un email déjà existant."""
        user_data = UserCreate(
            email=sample_users[0].email,
            password="password123",
            display_name="Duplicate User",
        )

        with pytest.raises(Exception):
            create_user(db_session, user_data)

    def test_create_user_long_display_name(self, db_session):
        """Test de création d'un utilisateur avec un nom très long."""
        long_name = "A" * 32  # Exactement la limite de 32 caractères
        user_data = UserCreate(
            email="longname@example.com",
            password="password123",
            display_name=long_name,
        )

        # Devrait réussir car c'est exactement la limite
        user = create_user(db_session, user_data)
        assert user.display_name == long_name

        # Vérifier que le dépassement de la limite est bloqué par Pydantic
        with pytest.raises(Exception):
            UserCreate(
                email="longname2@example.com",
                password="password123",
                display_name="A" * 33,  # Un caractère de trop
            )


class TestInviteUser:
    """Tests pour la fonction invite_user."""

    def test_invite_user_successfully(self, db_session, mock_email_service):
        """Test d'invitation réussie d'un utilisateur."""
        mixed_email = "NewInvite@Example.Com"
        user = invite_user(db_session, email=mixed_email, display_name="New Invited User", role=UserRole.USER)

        assert user.id is not None
        assert user.email == "newinvite@example.com"
        assert user.display_name == "New Invited User"
        assert user.role == UserRole.USER
        assert user.status == UserStatus.INVITED
        assert user.invite_token is not None
        assert user.invited_at is not None
        assert user.password_hash is None

        mock_email_service.send_invitation.assert_called_once()
        _, sent_args = mock_email_service.send_invitation.call_args
        assert sent_args["email"] == "newinvite@example.com"

    def test_invite_user_without_display_name(self, db_session, mock_email_service):
        """Test d'invitation d'un utilisateur sans nom d'affichage."""
        user = invite_user(db_session, email="invite2@example.com", display_name=None, role=UserRole.USER)

        assert user.display_name is None
        mock_email_service.send_invitation.assert_called_once()

    def test_invite_user_admin_role(self, db_session, mock_email_service):
        """Test d'invitation d'un utilisateur avec le rôle admin."""
        user = invite_user(
            db_session, email="admin_invite@example.com", display_name="Admin Invite", role=UserRole.ADMIN
        )

        assert user.role == UserRole.ADMIN
        mock_email_service.send_invitation.assert_called_once()

    def test_invite_user_duplicate_email(self, db_session, sample_users):
        """Test d'invitation d'un utilisateur avec un email déjà existant (insensible à la casse)."""
        existing_email = sample_users[0].email.upper()
        with pytest.raises(ValueError):
            invite_user(db_session, email=existing_email, display_name="Duplicate Invite", role=UserRole.USER)

    def test_invite_user_email_sending_failure(self, db_session, mock_email_service):
        """Test d'échec d'envoi d'email lors de l'invitation."""
        mock_email_service.send_invitation.side_effect = Exception("SMTP Error")

        user = invite_user(
            db_session, email="email_fail@example.com", display_name="Email Fail User", role=UserRole.USER
        )

        # L'utilisateur devrait quand même être créé
        assert user.id is not None
        assert user.status == UserStatus.INVITED

        # Mais l'email n'a pas pu être envoyé
        mock_email_service.send_invitation.assert_called_once()


class TestUpdateUser:
    """Tests pour la fonction update_user."""

    def test_update_user_email(self, db_session, sample_users):
        """Test de mise à jour de l'email d'un utilisateur."""
        user = sample_users[0]
        update_data = UserUpdate(email="NewEmail@Example.com")

        result = update_user(db_session, user.id, update_data)

        assert result is not None
        assert result.email == "newemail@example.com"

        db_user = get_user(db_session, user.id)
        assert db_user.email == "newemail@example.com"

    def test_update_user_display_name(self, db_session, sample_users):
        """Test de mise à jour du nom d'affichage."""
        user = sample_users[0]
        update_data = UserUpdate(display_name="Updated Name")

        result = update_user(db_session, user.id, update_data)

        assert result is not None
        assert result.display_name == "Updated Name"

    def test_update_user_password(self, db_session, sample_users):
        """Test de mise à jour du mot de passe."""
        user = sample_users[0]
        old_password_hash = user.password_hash
        update_data = UserUpdate(password="newpassword123")

        result = update_user(db_session, user.id, update_data)

        assert result is not None
        assert result.password_hash != old_password_hash
        assert result.password_hash is not None

    def test_update_user_role(self, db_session, sample_users):
        """Test de mise à jour du rôle."""
        user = sample_users[0]
        old_role = user.role
        update_data = UserUpdate(role=UserRole.ADMIN)

        result = update_user(db_session, user.id, update_data)

        assert result is not None
        assert result.role != old_role
        assert result.role == UserRole.ADMIN

    def test_update_user_multiple_fields(self, db_session, sample_users):
        """Test de mise à jour de plusieurs champs."""
        user = sample_users[0]
        update_data = UserUpdate(email="multi@example.com", display_name="Multi Update", language="en")

        result = update_user(db_session, user.id, update_data)

        assert result is not None
        assert result.email == "multi@example.com"
        assert result.display_name == "Multi Update"
        assert result.language == "en"

    def test_update_nonexistent_user(self, db_session):
        """Test de mise à jour d'un utilisateur qui n'existe pas."""
        update_data = UserUpdate(display_name="Ghost User")

        result = update_user(db_session, 999999, update_data)
        assert result is None

    def test_update_user_protected_field(self, db_session, sample_users):
        """Test que les champs protégés ne peuvent pas être mis à jour."""
        user = sample_users[0]
        original_id = user.id
        original_created_at = user.created_at

        # Essayer de mettre à jour un champ protégé (ça ne devrait pas marcher)
        update_data = UserUpdate(email="new@example.com")
        result = update_user(db_session, user.id, update_data)

        # L'ID et created_at ne devraient pas changer
        assert result.id == original_id
        assert result.created_at == original_created_at

    def test_update_user_partial_fields(self, db_session, sample_users):
        """Test de mise à jour partielle des champs."""
        user = sample_users[0]
        original_display_name = user.display_name
        original_language = user.language

        update_data = UserUpdate(email="partial@example.com")
        result = update_user(db_session, user.id, update_data)

        # Seul l'email devrait changer
        assert result.email == "partial@example.com"
        assert result.display_name == original_display_name
        assert result.language == original_language


class TestGetUserByInviteToken:
    """Tests pour la fonction get_user_by_invite_token."""

    def test_get_user_by_valid_invite_token(self, db_session, sample_users):
        """Test de récupération d'un utilisateur par token d'invitation valide."""
        invited_user = sample_users[1]  # L'utilisateur invité
        result = get_user_by_invite_token(db_session, invited_user.invite_token)

        assert result is not None
        assert result.id == invited_user.id
        assert result.email == invited_user.email

    def test_get_user_by_invalid_invite_token(self, db_session):
        """Test de récupération par token d'invitation invalide."""
        result = get_user_by_invite_token(db_session, "invalid_token")
        assert result is None

    def test_get_user_by_invite_token_wrong_status(self, db_session, sample_users):
        """Test de récupération par token pour un utilisateur non invité."""
        active_user = sample_users[0]  # L'utilisateur actif

        # Même si on lui donne un token, il ne devrait pas être trouvé
        active_user.invite_token = "some_token"
        db_session.commit()

        result = get_user_by_invite_token(db_session, "some_token")
        assert result is None


class TestSetPasswordFromInvite:
    """Tests pour la fonction set_password_from_invite."""

    def test_set_password_from_invite_successfully(self, db_session, sample_users):
        """Test de définition de mot de passe depuis une invitation."""
        invited_user = sample_users[1]  # L'utilisateur invité
        password = "new_password123"

        result = set_password_from_invite(db_session, invited_user, password)

        assert result is True

        # Vérifier que l'utilisateur a été mis à jour
        updated_user = get_user(db_session, invited_user.id)
        assert updated_user.status == UserStatus.ACTIVE
        assert updated_user.password_hash is not None
        assert updated_user.password_hash != password
        assert updated_user.invite_token is None
        assert updated_user.invited_at is None

    def test_set_password_from_invite_for_active_user(self, db_session, sample_users):
        """Test de définition de mot de passe pour un utilisateur actif."""
        active_user = sample_users[0]
        old_password_hash = active_user.password_hash
        password = "reset_password123"

        result = set_password_from_invite(db_session, active_user, password)

        assert result is True

        # Le mot de passe devrait être mis à jour
        updated_user = get_user(db_session, active_user.id)
        assert updated_user.password_hash != old_password_hash
        assert updated_user.status == UserStatus.ACTIVE

    def test_set_password_from_invite_for_deleted_user(self, db_session, sample_users):
        """Test de définition de mot de passe pour un utilisateur supprimé."""
        user = sample_users[0]
        user.status = UserStatus.DELETED
        db_session.commit()

        result = set_password_from_invite(db_session, user, "password123")
        assert result is False

    def test_set_password_from_invite_invalid_user(self, db_session):
        """Test de définition de mot de passe pour un utilisateur invalide."""
        fake_user = type("FakeUser", (), {"id": None})()

        result = set_password_from_invite(db_session, fake_user, "password123")
        assert result is False


class TestRequestPasswordReset:
    """Tests pour la fonction request_password_reset."""

    def test_request_password_reset_successfully(self, db_session, sample_users, mock_email_service):
        """Test de demande de réinitialisation de mot de passe réussie."""
        user = sample_users[0]
        original_token = user.invite_token

        result = request_password_reset(db_session, user.email)

        assert result is True

        # Vérifier que l'utilisateur a un nouveau token
        updated_user = get_user_by_email(db_session, user.email)
        assert updated_user.invite_token is not None
        assert updated_user.invite_token != original_token
        assert updated_user.invited_at is not None

        # Vérifier que l'email de réinitialisation a été envoyé
        mock_email_service.send_password_reset.assert_called_once()

    def test_request_password_reset_nonexistent_user(self, db_session, mock_email_service):
        """Test de demande de réinitialisation pour un utilisateur qui n'existe pas."""
        result = request_password_reset(db_session, "nonexistent@example.com")

        # Devrait retourner True pour des raisons de sécurité
        assert result is True

        # Aucun email ne devrait être envoyé
        mock_email_service.send_password_reset.assert_not_called()

    def test_request_password_reset_deleted_user(self, db_session, sample_users, mock_email_service):
        """Test de demande de réinitialisation pour un utilisateur désactivé."""
        user = sample_users[0]
        user.status = UserStatus.DELETED
        db_session.commit()

        result = request_password_reset(db_session, user.email)

        # Devrait retourner True pour des raisons de sécurité
        assert result is True

        # Aucun email ne devrait être envoyé
        mock_email_service.send_password_reset.assert_not_called()

    def test_request_password_reset_email_sending_failure(self, db_session, sample_users, mock_email_service):
        """Test d'échec d'envoi d'email de réinitialisation."""
        mock_email_service.send_password_reset.side_effect = Exception("SMTP Error")

        user = sample_users[0]
        result = request_password_reset(db_session, user.email)

        # Devrait retourner True même si l'email échoue
        assert result is True

        # Mais l'email a tenté d'être envoyé
        mock_email_service.send_password_reset.assert_called_once()


class TestGetUserByResetToken:
    """Tests pour la fonction get_user_by_reset_token."""

    def test_get_user_by_valid_reset_token(self, db_session, sample_users):
        """Test de récupération d'un utilisateur par token de réinitialisation valide."""
        user = sample_users[0]

        # Simuler une demande de réinitialisation
        request_password_reset(db_session, user.email)

        # Récupérer le token
        updated_user = get_user_by_email(db_session, user.email)
        result = get_user_by_reset_token(db_session, updated_user.invite_token)

        assert result is not None
        assert result.id == user.id
        assert result.email == user.email

    def test_get_user_by_invalid_reset_token(self, db_session):
        """Test de récupération par token de réinitialisation invalide."""
        result = get_user_by_reset_token(db_session, "invalid_token")
        assert result is None

    def test_get_user_by_reset_token_wrong_status(self, db_session, sample_users):
        """Test de récupération par token pour un utilisateur non actif."""
        invited_user = sample_users[1]  # L'utilisateur invité

        # Même s'il a un token, il ne devrait pas être trouvé pour la réinitialisation
        result = get_user_by_reset_token(db_session, invited_user.invite_token)
        assert result is None


class TestGetUserByAnyToken:
    """Tests pour la fonction get_user_by_any_token."""

    def test_get_user_by_any_token_invite(self, db_session, sample_users):
        """Test de récupération par token d'invitation."""
        invited_user = sample_users[1]
        result = get_user_by_any_token(db_session, invited_user.invite_token)

        assert result is not None
        assert result.id == invited_user.id

    def test_get_user_by_any_token_reset(self, db_session, sample_users):
        """Test de récupération par token de réinitialisation."""
        user = sample_users[0]

        # Simuler une demande de réinitialisation
        request_password_reset(db_session, user.email)

        # Récupérer le token
        updated_user = get_user_by_email(db_session, user.email)
        result = get_user_by_any_token(db_session, updated_user.invite_token)

        assert result is not None
        assert result.id == user.id

    def test_get_user_by_any_token_invalid(self, db_session):
        """Test de récupération par token invalide."""
        result = get_user_by_any_token(db_session, "invalid_token")
        assert result is None


class TestDeleteUser:
    """Tests pour la fonction delete_user."""

    def test_delete_user_successfully(self, db_session, sample_users):
        """Test de suppression réussie d'un utilisateur."""
        user = sample_users[0]
        user_id = user.id

        result = delete_user(db_session, user_id)

        assert result is True

        # Vérifier que l'utilisateur est marqué comme supprimé
        deleted_user = get_user(db_session, user_id)
        assert deleted_user is None

        # Mais il existe toujours dans la base
        raw_user = db_session.query(User).filter(User.id == user_id).first()
        assert raw_user is not None
        assert raw_user.status == UserStatus.DELETED

    def test_delete_nonexistent_user(self, db_session):
        """Test de suppression d'un utilisateur qui n'existe pas."""
        result = delete_user(db_session, 999999)
        assert result is False

    def test_delete_already_deleted_user(self, db_session, sample_users):
        """Test de suppression d'un utilisateur déjà supprimé."""
        user = sample_users[0]
        user.status = UserStatus.DELETED
        db_session.commit()

        result = delete_user(db_session, user.id)
        assert result is False


class TestAuthenticateUser:
    """Tests pour la fonction authenticate_user."""

    def test_authenticate_user_successfully(self, db_session, sample_users):
        """Test d'authentification réussie."""
        user = sample_users[0]
        result = authenticate_user(db_session, user.email, "password123")

    def test_authenticate_user_case_insensitive_email(self, db_session, sample_users):
        """L'authentification doit ignorer la casse de l'email."""
        user = sample_users[0]
        result = authenticate_user(db_session, user.email.upper(), "password123")

        assert result is not None
        assert result.id == user.id

        assert result is not None
        assert result.id == user.id
        assert result.email == user.email

    def test_authenticate_user_wrong_password(self, db_session, sample_users):
        """Test d'authentification avec mauvais mot de passe."""
        user = sample_users[0]
        result = authenticate_user(db_session, user.email, "wrong_password")

        assert result is None

    def test_authenticate_user_nonexistent_email(self, db_session):
        """Test d'authentification avec email inexistant."""
        result = authenticate_user(db_session, "nonexistent@example.com", "password123")
        assert result is None

    def test_authenticate_deleted_user(self, db_session, sample_users):
        """Test d'authentification d'un utilisateur supprimé."""
        user = sample_users[0]
        user.status = UserStatus.DELETED
        db_session.commit()

        result = authenticate_user(db_session, user.email, "password123")
        assert result is None

    def test_authenticate_invited_user(self, db_session, sample_users):
        """Test d'authentification d'un utilisateur invité (sans mot de passe)."""
        invited_user = sample_users[1]
        result = authenticate_user(db_session, invited_user.email, "password123")

        assert result is None


class TestCreateAdminUser:
    """Tests pour la fonction create_admin_user."""

    @patch.dict(
        "os.environ",
        {
            "DEFAULT_LANGUAGE": "en",
            "DEFAULT_ADMIN_EMAIL": "admin@test.com",
            "DEFAULT_ADMIN_PASSWORD": "secure_password",
            "DEFAULT_ADMIN_DISPLAY_NAME": "Super Admin",
        },
    )
    def test_create_admin_user_with_env_vars(self, db_session):
        """Test de création d'un admin avec les variables d'environnement."""
        admin = create_admin_user(db_session)

        assert admin.id is not None
        assert admin.email == "admin@test.com"
        assert admin.display_name == "Super Admin"
        assert admin.role == UserRole.ADMIN
        assert admin.language == "en"
        assert admin.status == UserStatus.ACTIVE
        assert admin.password_hash is not None
        assert admin.password_hash != "secure_password"

    @patch.dict("os.environ", {}, clear=True)
    def test_create_admin_user_default_values(self, db_session):
        """Test de création d'un admin avec les valeurs par défaut."""
        admin = create_admin_user(db_session)

        assert admin.id is not None
        assert admin.email == "admin@yaka.local"
        assert admin.display_name == "Admin"
        assert admin.role == UserRole.ADMIN
        assert admin.language == "en"  # Valeur par défaut si non spécifiée
        assert admin.status == UserStatus.ACTIVE
        assert admin.password_hash is not None
        assert admin.password_hash != "admin123"


class TestSecurityAndEdgeCases:
    """Tests de sécurité et cas particuliers."""

    def test_sql_injection_attempt_email(self, db_session):
        """Test de tentative d'injection SQL dans l'email."""
        malicious_email = "test'; DROP TABLE users; --"

        with pytest.raises(ValidationError):
            UserCreate(email=malicious_email, password="password123", display_name="SQL Injection Test")

    def test_xss_attempt_display_name(self, db_session):
        """Test de tentative XSS dans le nom d'affichage."""
        xss_name = "<script>alert('XSS')</script>"

        user_data = UserCreate(email="xss@example.com", password="password123", display_name=xss_name)

        user = create_user(db_session, user_data)
        assert user.display_name == xss_name

    def test_special_characters_in_email(self, db_session):
        """Test avec des caractères spéciaux dans l'email."""
        special_email = "test+special@example.com"

        user_data = UserCreate(email=special_email, password="password123", display_name="Special Email Test")

        user = create_user(db_session, user_data)
        assert user.email == special_email

    def test_unicode_characters(self, db_session):
        """Test avec des caractères Unicode."""
        user_data = UserCreate(
            email="unicode@test.com",
            password="password123",
            display_name="Unicode: éèàç",  # Court pour respecter la limite de 32 caractères
            language="fr",
        )

        user = create_user(db_session, user_data)
        assert user.display_name == "Unicode: éèàç"

    def test_very_long_password(self, db_session):
        """Test avec un mot de passe très long."""
        long_password = "a" * 1000

        user_data = UserCreate(email="longpass@example.com", password=long_password, display_name="Long Password Test")

        user = create_user(db_session, user_data)
        assert user.password_hash is not None
        assert user.password_hash != long_password

    def test_empty_strings(self, db_session):
        """Test avec des chaînes vides."""
        # Le display_name peut être vide (Optional)
        user_data = UserCreate(email="empty@example.com", password="password123", display_name="")
        assert user_data.display_name == ""

        # Test que le schéma permet effectivement les champs vides selon sa définition
        # (certains champs sont optionnels ou peuvent être vides)

    def test_concurrent_user_creation(self, db_session):
        """Test de création concurrente d'utilisateurs."""
        user1_data = UserCreate(
            email="concurrent1@example.com", password="password123", display_name="Concurrent User 1"
        )

        user2_data = UserCreate(
            email="concurrent2@example.com", password="password123", display_name="Concurrent User 2"
        )

        # Créer deux utilisateurs
        user1 = create_user(db_session, user1_data)
        user2 = create_user(db_session, user2_data)

        assert user1.id != user2.id
        assert user1.email != user2.email

    def test_password_hashing_consistency(self, db_session):
        """Test que le même mot de passe produit le même hash."""
        password = "test_password_123"

        user1_data = UserCreate(email="hash1@example.com", password=password, display_name="Hash Test 1")

        user2_data = UserCreate(email="hash2@example.com", password=password, display_name="Hash Test 2")

        user1 = create_user(db_session, user1_data)
        user2 = create_user(db_session, user2_data)

        # Les hash devraient être différents à cause du salage
        assert user1.password_hash != user2.password_hash
        assert user1.password_hash != password
        assert user2.password_hash != password

    def test_token_uniqueness(self, db_session, mock_email_service):
        """Test que les tokens d'invitation sont uniques."""
        # Inviter deux utilisateurs
        user1 = invite_user(db_session, "token1@example.com", "User 1", UserRole.USER)
        user2 = invite_user(db_session, "token2@example.com", "User 2", UserRole.USER)

        # Les tokens devraient être différents
        assert user1.invite_token != user2.invite_token
        assert len(user1.invite_token) > 0
        assert len(user2.invite_token) > 0

    def test_timezone_handling(self, db_session, mock_email_service):
        """Test de la gestion des fuseaux horaires."""
        invited_user = invite_user(db_session, "timezone@example.com", "Timezone User", UserRole.USER)

        assert invited_user.invited_at is not None
        # Note: SQLite ne stocke pas les timezone info, mais datetime devrait être présent
        assert isinstance(invited_user.invited_at, datetime)

        # La date devrait être récente (comparaison naive avec datetime naive)
        now = datetime.now()
        time_diff = abs((invited_user.invited_at.replace(tzinfo=None) - now).total_seconds())
        assert time_diff < 60  # Moins d'une minute de différence

    def test_database_error_handling(self, db_session):
        """Test de gestion des erreurs de base de données."""
        # Simuler une erreur de base de données
        with patch.object(db_session, "commit", side_effect=SQLAlchemyError("Database error")):
            user_data = UserCreate(email="error@example.com", password="password123", display_name="Error Test")

            with pytest.raises(SQLAlchemyError):
                create_user(db_session, user_data)

    def test_integrity_error_handling(self, db_session):
        """Test de gestion des erreurs d'intégrité."""
        # Créer un utilisateur
        user_data = UserCreate(email="integrity@example.com", password="password123", display_name="Integrity Test")
        create_user(db_session, user_data)

        # Essayer de créer un autre utilisateur avec le même email
        with pytest.raises(Exception):
            create_user(db_session, user_data)
