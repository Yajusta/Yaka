"""Routeur pour l'authentification."""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas import UserResponse, PasswordResetRequest
from ..services import user as user_service
from ..utils.security import Token, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from ..utils.dependencies import get_current_active_user

router = APIRouter(prefix="/auth", tags=["authentification"])


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Connexion utilisateur."""
    user = user_service.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: UserResponse = Depends(get_current_active_user)):
    """Obtenir les informations de l'utilisateur connecté."""
    return current_user


@router.post("/logout")
async def logout():
    """Déconnexion utilisateur (côté client)."""
    return {"message": "Déconnexion réussie"}


@router.post("/request-password-reset")
async def request_password_reset(
    request: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """Demander une réinitialisation de mot de passe."""
    from ..services import user as user_service
    user_service.request_password_reset(db, request.email)
    return {"message": "Si cet email existe, un lien de réinitialisation a été envoyé"}

