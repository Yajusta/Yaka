"""Routeur pour la gestion des utilisateurs."""

import contextlib
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, UserRole, UserStatus
from ..schemas import LanguageUpdate, SetPasswordPayload, UserCreate, UserListItem, UserResponse, UserUpdate
from ..services import user as user_service
from ..utils.dependencies import get_current_active_user, require_admin


class InvitePayload(BaseModel):
    email: str
    display_name: str | None = None
    role: UserRole = UserRole.VISITOR


router = APIRouter(prefix="/users", tags=["utilisateurs"])


@router.get("/", response_model=List[UserListItem])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Récupérer la liste des utilisateurs.

    - Si l'utilisateur courant est admin : renvoyer tous les champs.
    - Si l'utilisateur courant n'est pas admin : renvoyer la liste mais masquer les emails
      (email = None) pour préserver la confidentialité tout en permettant l'assignation.
    """
    users = user_service.get_users(db, skip=skip, limit=limit)

    result: list[dict] = []
    for u in users:
        item = {
            "id": u.id,
            "display_name": u.display_name,
            "role": u.role,
            "status": u.status,
            # Par défaut, ne pas exposer l'email aux non-admins
            "email": u.email if current_user.role == UserRole.ADMIN else None,
        }
        result.append(item)

    return result


@router.post("/", response_model=UserResponse)
async def create_user(user: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """Créer un nouvel utilisateur (Admin uniquement)."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Données invalides pour la création de l'utilisateur",
        )
    try:
        if user_service.get_user_by_email(db, email=user.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Un utilisateur avec cet email existe déjà"
            )
        return user_service.create_user(db=db, user=user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne lors de la création de l'utilisateur",
        ) from exc


@router.post("/invite", response_model=UserResponse)
async def invite_user(
    payload: InvitePayload, db: Session = Depends(get_db), current_user: User = Depends(require_admin)
):
    """Inviter un utilisateur par email (Admin uniquement)."""
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Données invalides pour l'invitation"
        )
    try:
        if user_service.get_user_by_email(db, email=payload.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Un utilisateur avec cet email existe déjà"
            )
        return user_service.invite_user(
            db=db, email=payload.email, display_name=payload.display_name, role=payload.role
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne lors de l'invitation de l'utilisateur",
        ) from exc


@router.get("/{user_id}", response_model=UserResponse)
async def read_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """Récupérer un utilisateur par son ID (Admin uniquement)."""
    db_user = user_service.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur non trouvé")
    return db_user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int, user_update: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)
):
    """Mettre à jour un utilisateur (Admin uniquement)."""
    if user_update is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Données invalides pour la mise à jour de l'utilisateur",
        )
    try:
        db_user = user_service.update_user(db, user_id=user_id, user_update=user_update)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne lors de la mise à jour de l'utilisateur",
        ) from exc
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur non trouvé")
    return db_user


@router.put("/me/language", response_model=UserResponse)
async def update_user_language(
    payload: LanguageUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """Mettre à jour la langue de l'utilisateur connecté."""
    if payload.language not in ["fr", "en"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Langue non supportée. Les langues supportées sont: fr, en"
        )

    # Mettre à jour directement le champ language
    current_user.language = payload.language
    db.commit()
    db.refresh(current_user)

    return current_user


@router.post("/{user_id}/resend-invitation", response_model=UserResponse)
async def resend_invitation(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """Renvoyer une invitation à un utilisateur existant (Admin uniquement)."""
    db_user = user_service.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur non trouvé")

    if db_user.status.lower() != UserStatus.INVITED.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="L'utilisateur n'est pas dans un état d'invitation"
        )

    # Vérifier le délai d'une minute
    from datetime import datetime, timezone

    if db_user.invited_at:
        # Convertir invited_at en timezone-aware si nécessaire
        if db_user.invited_at.tzinfo is None:
            # Si invited_at est timezone-naive, l'assumer en UTC
            invited_at_aware = db_user.invited_at.astimezone()
        else:
            invited_at_aware = db_user.invited_at

        time_diff = datetime.now().astimezone() - invited_at_aware
        if time_diff.total_seconds() < 60:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Une invitation a déjà été envoyée il y a moins d'une minute",
            )

    # Générer un nouveau token et mettre à jour l'horodatage
    import secrets

    new_token = secrets.token_urlsafe(32)
    new_invited_at = datetime.now().astimezone()

    db_user.invite_token = new_token
    # S'assurer que invited_at est timezone-aware
    db_user.invited_at = new_invited_at
    db.commit()
    db.refresh(db_user)

    # Renvoyer l'email d'invitation
    with contextlib.suppress(Exception):
        from ..services import email as email_service

        email_service.send_invitation(email=db_user.email, display_name=db_user.display_name, token=new_token)
    return db_user


@router.delete("/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """Supprimer un utilisateur (Admin uniquement)."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Vous ne pouvez pas supprimer votre propre compte"
        )
    try:
        success = user_service.delete_user(db, user_id=user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne lors de la suppression de l'utilisateur",
        ) from exc
    if success:
        return {"message": "Utilisateur supprimé avec succès"}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur non trouvé")


@router.post("/set-password")
async def set_password(payload: SetPasswordPayload, db: Session = Depends(get_db)):
    """Définir le mot de passe depuis le token d'invitation ou de réinitialisation.

    Body: { token, password }
    """
    user = user_service.get_user_by_any_token(db, token=payload.token)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token invalide ou expiré")

    if updated := user_service.set_password_from_invite(db, user=user, password=payload.password):
        return {"message": "Mot de passe défini avec succès"}
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Impossible de définir le mot de passe")
