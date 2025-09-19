"""Dépendances FastAPI pour l'authentification et l'autorisation."""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, UserRole
from .security import verify_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Obtenir l'utilisateur actuel à partir du token JWT."""
    from ..services.user import get_user_by_email  # Import local pour éviter la circularité

    token_data = verify_token(token, credentials_exception)
    if token_data is None or token_data.email is None:
        raise credentials_exception
    user = get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Obtenir l'utilisateur actuel actif."""
    return current_user


def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Vérifier que l'utilisateur actuel est un administrateur."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return current_user
