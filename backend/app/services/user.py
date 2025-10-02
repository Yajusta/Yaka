"""Service pour la gestion des utilisateurs."""

import contextlib
import datetime
import secrets
from asyncio import log
from os import getenv
from typing import List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from ..models import User, UserRole, UserStatus
from ..schemas import UserCreate, UserUpdate
from ..utils.security import get_password_hash, verify_password
from . import email as email_service

# Note: email_service requires SMTP_* env vars to be set for invitations to be sent


def get_system_timezone_datetime():
    """Retourne la date et heure actuelle dans le fuseau horaire du système."""
    return datetime.datetime.now().astimezone()


def get_user(db: Session, user_id: int) -> Optional[User]:
    """Récupérer un utilisateur par son ID."""
    return (
        db.query(User)
        .filter(
            and_(User.__table__.c.id == user_id, func.lower(User.__table__.c.status) != func.lower(UserStatus.DELETED))
        )
        .first()
    )


def get_user_by_email(db: Session, email: str | None) -> Optional[User]:
    """Recuperer un utilisateur par son email (insensible a la casse)."""
    if email is None:
        return None
    normalized_email = email.strip().lower()
    return (
        db.query(User)
        .filter(
            and_(
                func.lower(User.__table__.c.email) == normalized_email,
                func.lower(User.__table__.c.status) != func.lower(UserStatus.DELETED),
            )
        )
        .first()
    )


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    """Récupérer une liste d'utilisateurs."""
    return (
        db.query(User)
        .filter(func.lower(User.__table__.c.status) != func.lower(UserStatus.DELETED))
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_user(db: Session, user: UserCreate) -> User:
    """Créer un nouvel utilisateur traditionnel (mot de passe fourni)."""
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email.lower(),
        password_hash=hashed_password,
        display_name=user.display_name,
        role=user.role,
        language=user.language or "fr",
        status=UserStatus.ACTIVE,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def invite_user(db: Session, email: str, display_name: str | None, role: UserRole) -> User:
    """Creer un utilisateur en tant qu'invite et envoyer un email d'invitation."""
    invite_token = secrets.token_urlsafe(32)
    invited_at = get_system_timezone_datetime()
    normalized_email = email.strip().lower()

    existing_user = get_user_by_email(db, normalized_email)
    if existing_user and existing_user.status != UserStatus.DELETED:
        raise ValueError("Un utilisateur avec cet email existe deja")

    db_user = User(
        email=normalized_email,
        display_name=display_name,
        role=role,
        language="fr",
        status=UserStatus.INVITED,
        invite_token=invite_token,
        invited_at=invited_at,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    try:
        email_service.send_invitation(email=normalized_email, display_name=display_name, token=invite_token)
    except Exception as exc:
        print(f"ERROR: Erreur lors de l'envoi de l'email d'invitation a {normalized_email}: {exc}")
    return db_user


def update_user(db: Session, user_id: int, user_update: UserUpdate) -> Optional[User]:
    """Mettre à jour un utilisateur."""
    db_user = get_user(db, user_id)
    if not db_user:
        return None

    update_data = user_update.model_dump(exclude_unset=True)

    if "email" in update_data and update_data["email"] is not None:
        normalized_email = update_data["email"].strip().lower()
        update_data["email"] = normalized_email
        existing_user = get_user_by_email(db, normalized_email)
        if existing_user and existing_user.id != user_id:
            raise ValueError("Un utilisateur avec cet email existe deja")

    # Hacher le nouveau mot de passe si fourni
    if "password" in update_data:
        update_data["password_hash"] = get_password_hash(update_data.pop("password"))

    for field, value in update_data.items():
        if field not in User.PROTECTED_FIELDS:
            setattr(db_user, field, value)

    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_by_invite_token(db: Session, token: str) -> Optional[User]:
    return (
        db.query(User)
        .filter(
            and_(
                User.__table__.c.invite_token == token,
                func.lower(User.__table__.c.status) == func.lower(UserStatus.INVITED),
            )
        )
        .first()
    )


def set_password_from_invite(db: Session, user: User, password: str) -> bool:
    # Ensure we operate on a loaded ORM instance from the DB so status comparisons
    # produce a Python value (not a SQL expression/ColumnElement)
    user_id = getattr(user, "id", None)
    if not user_id:
        return False

    db_user = get_user(db, user_id)
    if not db_user:
        return False

    # Permettre la définition de mot de passe pour les utilisateurs invités ET pour la réinitialisation
    if db_user.status not in [UserStatus.INVITED, UserStatus.ACTIVE]:
        return False

    db_user.password_hash = get_password_hash(password)
    db_user.status = UserStatus.ACTIVE
    db_user.invite_token = None
    db_user.invited_at = None
    db.commit()
    db.refresh(db_user)
    return True


def request_password_reset(db: Session, email: str) -> bool:
    """Demander une réinitialisation de mot de passe."""
    user = get_user_by_email(db, email)
    if not user or user.status != UserStatus.ACTIVE:
        # Ne pas révéler si l'utilisateur existe ou non pour des raisons de sécurité
        return True

    reset_token = secrets.token_urlsafe(32)
    user.invite_token = reset_token  # Réutiliser le champ invite_token pour la réinitialisation
    user.invited_at = get_system_timezone_datetime()

    db.commit()

    with contextlib.suppress(Exception):
        email_service.send_password_reset(email=email, display_name=user.display_name, token=reset_token)
    return True


def get_user_by_reset_token(db: Session, token: str) -> Optional[User]:
    """Récupérer un utilisateur par son token de réinitialisation (pour utilisateurs actifs)."""
    return (
        db.query(User)
        .filter(
            and_(
                User.__table__.c.invite_token == token,
                func.lower(User.__table__.c.status) == func.lower(UserStatus.ACTIVE),
            )
        )
        .first()
    )


def get_user_by_any_token(db: Session, token: str) -> Optional[User]:
    """Récupérer un utilisateur par son token (invitation ou réinitialisation)."""
    return db.query(User).filter(User.__table__.c.invite_token == token).first()


def delete_user(db: Session, user_id: int) -> bool:
    """Supprimer un utilisateur (suppression logique)."""
    db_user = get_user(db, user_id)
    if not db_user:
        return False

    db_user.status = UserStatus.DELETED
    db.commit()
    return True


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authentifier un utilisateur."""
    normalized_email = email.strip().lower()
    if user := get_user_by_email(db, normalized_email):
        return (
            user
            if user.status == UserStatus.ACTIVE and verify_password(password, getattr(user, "password_hash"))
            else None
        )
    else:
        return None


def create_admin_user(db: Session) -> User:
    """Créer un utilisateur administrateur par défaut."""
    default_lang = getenv("DEFAULT_LANGUAGE", "en")
    default_email = getenv("DEFAULT_ADMIN_EMAIL", "admin@yaka.local").lower()
    default_password = getenv("DEFAULT_ADMIN_PASSWORD", "Admin123")
    default_display_name = getenv("DEFAULT_ADMIN_DISPLAY_NAME", "Admin")
    admin_data = UserCreate(
        email=default_email,
        password=default_password,
        display_name=default_display_name,
        role=UserRole.ADMIN,
        language=default_lang,
    )
    return create_user(db, admin_data)
