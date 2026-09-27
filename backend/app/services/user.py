"""Service pour la gestion des utilisateurs."""

import contextlib
import datetime
import logging
import secrets
from os import getenv
from typing import Callable, List, Optional

from pydantic import ValidationError
from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from ..models import User, UserRole, UserStatus
from ..models.helpers import get_system_timezone_datetime
from ..schemas import UserCreate, UserUpdate
from ..schemas.user import _validate_password_strength
from ..utils.demo_mode import is_demo_mode
from ..utils.security import (
    dummy_password_hash,
    get_password_hash,
    verify_password,
)
from . import email as email_service

# Note: email_service requires SMTP_* env vars to be set for invitations to be sent

logger = logging.getLogger(__name__)

# Mot de passe public de l'administrateur en mode démo (documenté dans le README).
DEMO_ADMIN_PASSWORD = "Admin123"  # nosec B105
# Email historique de l'administrateur initial (valeur par défaut de DEFAULT_ADMIN_EMAIL)
LEGACY_ADMIN_EMAIL = "admin@yaka.local"

# Durée de vie des jetons (invite_token) : réinitialisation d'un compte ACTIVE,
# invitation d'un compte INVITED. Comptée depuis invited_at.
RESET_TOKEN_TTL = datetime.timedelta(hours=1)
INVITE_TOKEN_TTL = datetime.timedelta(days=7)
# Délai minimal avant de remplacer un jeton en attente (renvoi d'email)
TOKEN_RESEND_DELAY = datetime.timedelta(seconds=60)


def default_admin_email() -> str:
    """Email de l'administrateur initial (DEFAULT_ADMIN_EMAIL, admin@yaka.local par défaut)."""
    return getenv("DEFAULT_ADMIN_EMAIL", LEGACY_ADMIN_EMAIL).lower()


def revoke_sessions(user: User) -> None:
    """Invalider les jetons de session émis pour l'utilisateur (commit par l'appelant).

    Incrément côté SQL : deux révocations concurrentes ne se confondent pas.
    La nouvelle valeur n'est lisible qu'après commit/refresh.
    """
    user.token_version = User.token_version + 1


def logout_user(db: Session, user: User) -> None:
    """Déconnexion : invalide tous les jetons de session de l'utilisateur.

    Sauf en mode démo : les comptes y sont partagés (mots de passe publics),
    la déconnexion d'un visiteur fermerait la session de tous les autres.
    """
    if is_demo_mode():
        return
    revoke_sessions(user)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise


def clear_pending_token(user: User) -> None:
    """Invalider le jeton d'invitation/réinitialisation en attente (commit par l'appelant)."""
    user.invite_token = None
    user.invited_at = None


def set_user_password(user: User, password: str, *, must_change: bool = False) -> None:
    """Définir le mot de passe (commit par l'appelant).

    Point unique : invalide aussi le jeton en attente et les sessions existantes.
    """
    user.password_hash = get_password_hash(password)
    user.must_change_password = must_change
    clear_pending_token(user)
    revoke_sessions(user)


def token_age(user: User) -> Optional[datetime.timedelta]:
    """Âge du jeton en attente (None si invited_at absent).

    SQLite restitue invited_at sans fuseau : il a été enregistré en heure locale.
    """
    if user.invited_at is None:
        return None
    invited_at = user.invited_at
    if invited_at.tzinfo is None:
        invited_at = invited_at.astimezone()
    return get_system_timezone_datetime() - invited_at


def token_recently_issued(user: User) -> bool:
    """Vrai si un jeton en attente a été émis il y a moins de TOKEN_RESEND_DELAY."""
    age = token_age(user)
    return bool(user.invite_token) and age is not None and age < TOKEN_RESEND_DELAY


def _unexpired_token_user(db: Session, user: Optional[User]) -> Optional[User]:
    """Retourne l'utilisateur si son jeton est encore valide, sinon efface le jeton."""
    if user is None:
        return None
    ttl = INVITE_TOKEN_TTL if user.status == UserStatus.INVITED else RESET_TOKEN_TTL
    age = token_age(user)
    if age is not None and age <= ttl:
        return user
    clear_pending_token(user)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    return None


def send_quietly(send: Callable[..., None], **kwargs) -> None:
    """Envoyer un email sans propager l'erreur (journalisée avec la trace)."""
    try:
        send(**kwargs)
    except Exception:
        logger.exception("Échec de l'envoi d'un email")


def _send_now(func: Callable[..., None], *args, **kwargs) -> None:
    """Planificateur par défaut : exécution immédiate (scripts, appels hors requête)."""
    func(*args, **kwargs)


def _defer_token_email(
    user: User,
    token: str,
    board_uid: Optional[str],
    defer: Callable[..., None],
) -> None:
    """Planifier l'email portant le jeton : invitation (INVITED) ou réinitialisation."""
    send = (
        email_service.send_invitation
        if user.status == UserStatus.INVITED
        else email_service.send_password_reset
    )
    defer(
        send_quietly,
        send,
        email=user.email,
        display_name=user.display_name,
        token=token,
        board_uid=board_uid,
    )


def issue_pending_token(
    db: Session,
    user: User,
    board_uid: Optional[str] = None,
    defer: Callable[..., None] = _send_now,
) -> bool:
    """Émettre un nouveau jeton (invitation/réinitialisation) et planifier son email.

    Retourne False sans rien faire si un jeton a été émis il y a moins de
    TOKEN_RESEND_DELAY. `defer` planifie l'envoi (ex. BackgroundTasks.add_task).
    """
    if token_recently_issued(user):
        return False
    # Le champ invite_token sert aussi de jeton de réinitialisation
    token = secrets.token_urlsafe(32)
    previous = user.invite_token
    # Remplacement conditionnel (compare-and-set) : de deux demandes concurrentes,
    # une seule remplace le jeton lu, l'autre est traitée comme une rafale
    same_token = (
        User.invite_token.is_(None)
        if previous is None
        else User.invite_token == previous
    )
    try:
        replaced = (
            db.query(User)
            .filter(User.id == user.id, same_token)
            .update(
                {
                    User.invite_token: token,
                    User.invited_at: get_system_timezone_datetime(),
                },
                synchronize_session=False,
            )
        )
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    # Pas de refresh : le commit a expiré l'instance, rechargée à la lecture
    if not replaced:
        return False
    _defer_token_email(user, token, board_uid, defer)
    return True


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
    defer: Callable[..., None] = _send_now,
) -> User:
    """Creer un utilisateur en tant qu'invite et envoyer un email d'invitation.

    `defer` planifie l'envoi (ex. BackgroundTasks.add_task) ; immédiat par défaut.
    """
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

    _defer_token_email(db_user, invite_token, board_uid, defer)
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
    # Mot de passe défini par un administrateur : plus aléatoire ni public ;
    # jeton en attente et sessions invalidés
    new_password = update_data.pop("password", None)
    if new_password is not None:
        set_user_password(db_user, new_password)
        # Le jeton d'invitation vient d'être effacé : un compte INVITED resterait
        # sans moyen de connexion, il devient actif avec ce mot de passe
        if db_user.status == UserStatus.INVITED and "status" not in update_data:
            db_user.status = UserStatus.ACTIVE

    # Rôle modifié : les jetons existants sont révoqués (déjà fait si nouveau mot de passe)
    elif "role" in update_data and update_data["role"] != db_user.role:
        revoke_sessions(db_user)

    for field, value in update_data.items():
        if field not in User.PROTECTED_FIELDS:
            setattr(db_user, field, value)

    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_by_invite_token(db: Session, token: str) -> Optional[User]:
    user = (
        db.query(User)
        .filter(
            and_(
                User.__table__.c.invite_token == token,
                func.lower(User.__table__.c.status) == UserStatus.INVITED.value.lower(),
            )
        )
        .first()
    )
    return _unexpired_token_user(db, user)


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

    set_user_password(db_user, password)
    db_user.status = UserStatus.ACTIVE
    db.commit()
    db.refresh(db_user)
    return True


def request_password_reset(
    db: Session,
    email: str,
    board_uid: Optional[str] = None,
    defer: Callable[..., None] = _send_now,
) -> bool:
    """Demander une réinitialisation de mot de passe.

    Si l'utilisateur est INVITED (n'a pas encore validé son invitation),
    renvoie un email d'invitation au lieu d'un email de reset.
    Si l'utilisateur est ACTIVE, envoie un email de reset password.
    Pour tous les autres cas (inexistant, DELETED), ou si un jeton a été émis il y a
    moins de TOKEN_RESEND_DELAY, retourne True sans rien faire pour des raisons de
    sécurité (ne pas révéler l'existence ou non de l'utilisateur).
    `defer` planifie l'envoi (ex. BackgroundTasks.add_task) ; immédiat par défaut.
    """
    user = get_user_by_email(db, email)

    if user and user.status in (UserStatus.INVITED, UserStatus.ACTIVE):
        # Demande en rafale (jeton tout juste émis) : ignorée silencieusement
        issue_pending_token(db, user, board_uid, defer)
    return True


def get_user_by_reset_token(db: Session, token: str) -> Optional[User]:
    """Récupérer un utilisateur par son token de réinitialisation (pour utilisateurs actifs)."""
    user = (
        db.query(User)
        .filter(
            and_(
                User.__table__.c.invite_token == token,
                func.lower(User.__table__.c.status) == UserStatus.ACTIVE.value.lower(),
            )
        )
        .first()
    )
    return _unexpired_token_user(db, user)


def get_user_by_any_token(db: Session, token: str) -> Optional[User]:
    """Récupérer un utilisateur par son token (invitation ou réinitialisation)."""
    user = db.query(User).filter(User.__table__.c.invite_token == token).first()
    return _unexpired_token_user(db, user)


def delete_user(db: Session, user_id: int) -> bool:
    """Supprimer un utilisateur (suppression logique)."""
    db_user = get_user(db, user_id)
    if not db_user:
        return False

    db_user.status = UserStatus.DELETED
    revoke_sessions(db_user)
    db.commit()
    return True


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authentifier un utilisateur.

    bcrypt s'exécute dans tous les cas (hash factice si le compte est inconnu ou
    inactif) : le temps de réponse ne révèle pas l'existence du compte.
    """
    user = get_user_by_email(db, email.strip().lower())
    if not user or user.status != UserStatus.ACTIVE or not user.password_hash:
        verify_password(password, dummy_password_hash())
        return None
    return user if verify_password(password, user.password_hash) else None


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
    set_user_password(user, new_password)
    try:
        db.commit()
        db.refresh(user)
    except SQLAlchemyError:
        db.rollback()
        raise
