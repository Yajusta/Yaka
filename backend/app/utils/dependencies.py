"""Dépendances FastAPI pour l'authentification et l'autorisation."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from ..models import User, UserRole, UserStatus
from ..multi_database import get_dynamic_db as get_db
from ..multi_database import get_effective_board_uid
from .security import verify_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Code d'erreur (detail du 403) reconnu par l'intercepteur axios du frontend
# (shared/services/api.tsx) pour afficher l'écran de changement de mot de passe.
PASSWORD_CHANGE_REQUIRED = "password_change_required"

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """Obtenir l'utilisateur actuel à partir du token JWT.

    Le jeton doit désigner le compte existant (claims `sub` et `uid`), avoir
    été émis sur le board de la requête (claim `board`),
    porter la version de jetons courante de l'utilisateur (claim `ver`) et
    l'utilisateur doit être actif.
    """
    token_data = verify_token(token, credentials_exception)
    if token_data is None or token_data.email is None or token_data.uid is None:
        raise credentials_exception
    if token_data.board != get_effective_board_uid():
        raise credentials_exception
    # Recherche par clé primaire ; l'email doit toujours correspondre (un
    # changement d'email invalide les jetons émis auparavant)
    user = db.get(User, token_data.uid)
    if (
        user is None
        or user.email.lower() != token_data.email.lower()
        or user.status != UserStatus.ACTIVE
        or token_data.ver != user.token_version
    ):
        raise credentials_exception
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Obtenir l'utilisateur actuel actif.

    Tant qu'un changement de mot de passe est exigé, seules les routes qui
    dépendent directement de get_current_user (profil, changement de mot de
    passe, langue) restent accessibles.
    """
    if current_user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=PASSWORD_CHANGE_REQUIRED,
        )
    return current_user


def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Vérifier que l'utilisateur actuel est un administrateur."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )
    return current_user
