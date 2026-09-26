"""Service pour la gestion des utilisateurs."""

import contextlib
import datetime
import logging
import secrets
from os import getenv
from typing import List, Optional

from pydantic import ValidationError
from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from ..models import User, UserRole, UserStatus
from ..schemas import UserCreate, UserUpdate
from ..schemas.user import _validate_password_strength
from ..utils.demo_mode import is_demo_mode
from ..utils.security import get_password_hash, verify_password
from . import email as email_service

# Note: email_service requires SMTP_* env vars to be set for invitations to be sent

logger = logging.getLogger(__name__)

# Mot de passe public de l'administrateur en mode démo (documenté dans le README).
DEMO_ADMIN_PASSWORD = "Admin123"  # nosec B105
# Email historique de l'administrateur initial (valeur par défaut de DEFAULT_ADMIN_EMAIL)
LEGACY_ADMIN_EMAIL = "admin@yaka.local"


def default_admin_email() -> str:
    """Email de l'administrateur initial (DEFAULT_ADMIN_EMAIL, admin@yaka.local par défaut)."""
    return getenv("DEFAULT_ADMIN_EMAIL", LEGACY_ADMIN_EMAIL).lower()


def get_system_timezone_datetime():
    """Retourne la date et heure actuelle dans le fuseau horaire du système."""
    return datetime.datetime.now().astimezone()


def get_user(db: Session, user_id: int) -> Optional[User]:
    """Récupérer un utilisateur par son ID."""
    return (
        db.query(User)
        .filter(
            and_(
                User.__table__.c.id == user_id,
                func.lower(User.__table__.c.status) != UserStatus.DELETED.value.lower(),
            )
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
                func.lower(User.__table__.c.status) != UserStatus.DELETED.value.lower(),
            )
        )
        .first()
    )


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    """Récupérer une liste d'utilisateurs."""
    return (
        db.query(User)
        .filter(func.lower(User.__table__.c.status) != UserStatus.DELETED.value.lower())
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_user(
    db: Session, user: UserCreate, must_change_password: bool = False
) -> User:
    """Créer un nouvel utilisateur traditionnel (mot de passe fourni)."""
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email.lower(),
        password_hash=hashed_password,
        display_name=user.display_name,
        role=user.role,
        language=user.language or "fr",
        status=UserStatus.ACTIVE,
        must_change_password=must_change_password,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def invite_user(
    db: Session,
    email: str,
    display_name: str | None,
    role: UserRole,
    board_uid: Optional[str] = None,
) -> User:
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
        email_service.send_invitation(
            email=normalized_email,
            display_name=display_name,
            token=invite_token,
            board_uid=board_uid,
        )
    except Exception as exc:
        print(
            f"ERROR: Erreur lors de l'envoi de l'email d'invitation a {normalized_email}: {exc}"
        )
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
        # Mot de passe défini par un administrateur : plus aléatoire ni public
        db_user.must_change_password = False

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
                func.lower(User.__table__.c.status) == UserStatus.INVITED.value.lower(),
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
    db_user.must_change_password = False
    db_user.status = UserStatus.ACTIVE
    db_user.invite_token = None
    db_user.invited_at = None
    db.commit()
    db.refresh(db_user)
    return True


def request_password_reset(
    db: Session, email: str, board_uid: Optional[str] = None
) -> bool:
    """Demander une réinitialisation de mot de passe.

    Si l'utilisateur est INVITED (n'a pas encore validé son invitation),
    renvoie un email d'invitation au lieu d'un email de reset.
    Si l'utilisateur est ACTIVE, envoie un email de reset password.
    Pour tous les autres cas (inexistant, DELETED), retourne True sans rien faire
    pour des raisons de sécurité (ne pas révéler l'existence ou non de l'utilisateur).
    """
    user = get_user_by_email(db, email)

    # Cas 1: Utilisateur inexistant ou supprimé - Ne rien faire pour des raisons de sécurité
    if not user or user.status == UserStatus.DELETED:
        return True

    # Cas 2: Utilisateur invité mais pas encore actif - Renvoyer l'email d'invitation
    if user.status == UserStatus.INVITED:
        invite_token = secrets.token_urlsafe(32)
        user.invite_token = invite_token
        user.invited_at = get_system_timezone_datetime()
        db.commit()

        with contextlib.suppress(Exception):
            email_service.send_invitation(
                email=email,
                display_name=user.display_name,
                token=invite_token,
                board_uid=board_uid,
            )
        return True

    # Cas 3: Utilisateur actif - Envoyer l'email de réinitialisation de mot de passe
    if user.status == UserStatus.ACTIVE:
        reset_token = secrets.token_urlsafe(32)
        user.invite_token = (
            reset_token  # Réutiliser le champ invite_token pour la réinitialisation
        )
        user.invited_at = get_system_timezone_datetime()
        db.commit()

        with contextlib.suppress(Exception):
            email_service.send_password_reset(
                email=email,
                display_name=user.display_name,
                token=reset_token,
                board_uid=board_uid,
            )
        return True

    # Sécurité: retourner True pour tous les autres cas
    return True


def get_user_by_reset_token(db: Session, token: str) -> Optional[User]:
    """Récupérer un utilisateur par son token de réinitialisation (pour utilisateurs actifs)."""
    return (
        db.query(User)
        .filter(
            and_(
                User.__table__.c.invite_token == token,
                func.lower(User.__table__.c.status) == UserStatus.ACTIVE.value.lower(),
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
            if user.status == UserStatus.ACTIVE
            and verify_password(password, user.password_hash)
            else None
        )
    else:
        return None


def generate_initial_password() -> str:
    """Génère un mot de passe aléatoire respectant les règles de complexité."""
    while True:
        with contextlib.suppress(ValueError):
            return _validate_password_strength(secrets.token_urlsafe(16))


# Variable d'environnement à l'origine de chaque champ de l'administrateur initial
_ADMIN_ENV_VARS = {
    "email": "DEFAULT_ADMIN_EMAIL",
    "password": "DEFAULT_ADMIN_PASSWORD",
    "display_name": "DEFAULT_ADMIN_DISPLAY_NAME",
    "language": "DEFAULT_LANGUAGE",
}


def create_admin_user(db: Session) -> User:
    """Créer un utilisateur administrateur par défaut.

    Mot de passe : DEFAULT_ADMIN_PASSWORD s'il est défini, le mot de passe public
    en mode démo, sinon un mot de passe aléatoire logué une seule fois et à changer
    à la première connexion.
    """
    default_lang = getenv("DEFAULT_LANGUAGE", "en")
    default_email = default_admin_email()
    default_display_name = getenv("DEFAULT_ADMIN_DISPLAY_NAME", "Admin")
    # Une valeur vide (transmise par docker-compose) équivaut à une variable absente
    default_password = getenv("DEFAULT_ADMIN_PASSWORD")
    generated = False
    if is_demo_mode():
        default_password = default_password or DEMO_ADMIN_PASSWORD
    elif not default_password or default_password == DEMO_ADMIN_PASSWORD:
        # Le mot de passe public (ancienne valeur documentée) serait de toute
        # façon remplacé au démarrage par secure_default_accounts : on génère
        # directement un mot de passe aléatoire.
        if default_password:
            logger.warning(
                "DEFAULT_ADMIN_PASSWORD utilise le mot de passe public %s : ignoré "
                "hors mode démo",
                DEMO_ADMIN_PASSWORD,
            )
        default_password = generate_initial_password()
        generated = True
    try:
        admin_data = UserCreate(
            email=default_email,
            password=default_password,
            display_name=default_display_name,
            role=UserRole.ADMIN,
            language=default_lang,
        )
    except ValidationError as exc:
        errors = "; ".join(
            f"{_ADMIN_ENV_VARS.get(str(err['loc'][0]) if err['loc'] else '', '?')}"
            f" : {err['msg']}"
            for err in exc.errors()
        )
        raise ValueError(
            f"Impossible de créer l'administrateur initial ({default_email}) : "
            f"configuration invalide ({errors})"
        ) from None

    admin = create_user(db, admin_data, must_change_password=generated)
    if generated:
        logger.warning(
            "Administrateur initial créé : %s / mot de passe : %s "
            "(affiché une seule fois, changement exigé à la première connexion)",
            default_email,
            default_password,
        )
    return admin


def change_password(
    db: Session, user: User, current_password: str, new_password: str
) -> None:
    """Changer le mot de passe de l'utilisateur connecté et lever le changement obligatoire."""
    if not user.password_hash or not verify_password(
        current_password, user.password_hash
    ):
        raise ValueError("Mot de passe actuel incorrect")
    if current_password == new_password:
        raise ValueError("Le nouveau mot de passe doit être différent de l'actuel")
    user.password_hash = get_password_hash(new_password)
    user.must_change_password = False
    try:
        db.commit()
        db.refresh(user)
    except SQLAlchemyError:
        db.rollback()
        raise
