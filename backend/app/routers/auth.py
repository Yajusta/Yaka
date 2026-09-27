"""Routeur pour l'authentification."""

import os

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..models import User
from ..multi_database import get_current_board_uid
from ..multi_database import get_dynamic_db as get_db
from ..schemas import (
    PasswordChange,
    PasswordChangeResponse,
    PasswordResetRequest,
    UserResponse,
)
from ..services import user as user_service
from ..utils.dependencies import get_current_user
from ..utils.security import Token, create_user_access_token

router = APIRouter(prefix="/auth", tags=["authentification"])


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """Connexion utilisateur."""
    user = user_service.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_user_access_token(user)
    # "bearer" est le type de jeton OAuth2, pas un secret
    return {"access_token": access_token, "token_type": "bearer"}  # nosec B105


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Obtenir les informations de l'utilisateur connecté.

    Accessible même si un changement de mot de passe est exigé.
    """
    return current_user


@router.post("/change-password", response_model=PasswordChangeResponse)
async def change_password(
    payload: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Changer son propre mot de passe (lève le changement obligatoire).

    Les jetons existants sont révoqués : un nouveau jeton est renvoyé pour que
    la session courante reste ouverte.
    """
    try:
        user_service.change_password(
            db, current_user, payload.current_password, payload.new_password
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return PasswordChangeResponse(
        **UserResponse.model_validate(current_user).model_dump(),
        access_token=create_user_access_token(current_user),
    )


@router.post("/logout")
async def logout(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Déconnexion : révoque tous les jetons de session de l'utilisateur."""
    user_service.logout_user(db, current_user)
    return {"message": "Déconnexion réussie"}


@router.post("/request-password-reset")
async def request_password_reset(
    request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Demander une réinitialisation de mot de passe.

    Le board du lien est celui du chemin (validé par BoardContextMiddleware),
    jamais une valeur fournie par le client. L'email part en tâche de fond :
    la réponse est identique et immédiate, que le compte existe ou non.
    """
    user_service.request_password_reset(
        db,
        request.email,
        get_current_board_uid(),
        defer=background_tasks.add_task,
    )
    return {"message": "Si cet email existe, un lien de réinitialisation a été envoyé"}


@router.get("/ai-features")
async def check_ai_features():
    """Vérifie si les fonctionnalités IA sont disponibles."""
    # Configuration lue depuis l'environnement du processus (chargé au démarrage)
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    llm_model = os.getenv("LLM_MODEL", "")

    # Les fonctionnalités IA sont disponibles si les deux variables sont configurées
    ai_available = bool(openai_api_key and llm_model)

    return {"ai_available": ai_available}
