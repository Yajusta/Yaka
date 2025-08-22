"""Routeur pour la gestion des utilisateurs."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas import UserCreate, UserUpdate, UserResponse, SetPasswordPayload, UserListItem
from ..services import user as user_service
from ..utils.dependencies import require_admin, get_current_active_user
from ..models import User, UserRole, UserStatus
from pydantic import BaseModel


class InvitePayload(BaseModel):
    email: str
    display_name: str | None = None
    role: UserRole = UserRole.USER


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
    db_user = user_service.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Un utilisateur avec cet email existe déjà"
        )
    return user_service.create_user(db=db, user=user)


@router.post("/invite", response_model=UserResponse)
async def invite_user(
    payload: InvitePayload, db: Session = Depends(get_db), current_user: User = Depends(require_admin)
):
    """Inviter un utilisateur par email (Admin uniquement)."""
    existing = user_service.get_user_by_email(db, email=payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Un utilisateur avec cet email existe déjà"
        )
    return user_service.invite_user(db=db, email=payload.email, display_name=payload.display_name, role=payload.role)


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
    db_user = user_service.update_user(db, user_id=user_id, user_update=user_update)
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur non trouvé")
    return db_user


@router.post("/{user_id}/resend-invitation", response_model=UserResponse)
async def resend_invitation(
    user_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)
):
    """Renvoyer une invitation à un utilisateur existant (Admin uniquement)."""
    db_user = user_service.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur non trouvé")

    if db_user.status != UserStatus.INVITED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="L'utilisateur n'est pas dans un état d'invitation"
        )

    # Vérifier le délai d'une minute
    from datetime import datetime, timezone
    if db_user.invited_at:
        # Convertir invited_at en timezone-aware si nécessaire
        if db_user.invited_at.tzinfo is None:
            # Si invited_at est timezone-naive, l'assumer en UTC
            invited_at_aware = db_user.invited_at.replace(tzinfo=timezone.utc)
        else:
            invited_at_aware = db_user.invited_at

        time_diff = datetime.now(timezone.utc) - invited_at_aware
        if time_diff.total_seconds() < 60:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Une invitation a déjà été envoyée il y a moins d'une minute"
            )

    # Générer un nouveau token et mettre à jour l'horodatage
    import secrets
    new_token = secrets.token_urlsafe(32)
    new_invited_at = datetime.now(timezone.utc)

    db_user.invite_token = new_token
    # S'assurer que invited_at est timezone-aware
    db_user.invited_at = new_invited_at
    db.commit()
    db.refresh(db_user)

    # Renvoyer l'email d'invitation
    try:
        from ..services import email as email_service
        email_service.send_invitation(email=db_user.email, display_name=db_user.display_name, token=new_token)
    except Exception:
        pass  # Ne pas échouer si l'email ne peut pas être envoyé

    return db_user


@router.delete("/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """Supprimer un utilisateur (Admin uniquement)."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Vous ne pouvez pas supprimer votre propre compte"
        )

    success = user_service.delete_user(db, user_id=user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur non trouvé")
    return {"message": "Utilisateur supprimé avec succès"}


@router.post("/set-password")
async def set_password(payload: SetPasswordPayload, db: Session = Depends(get_db)):
    """Définir le mot de passe depuis le token d'invitation ou de réinitialisation.

    Body: { token, password }
    """
    user = user_service.get_user_by_any_token(db, token=payload.token)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token invalide ou expiré")

    updated = user_service.set_password_from_invite(db, user=user, password=payload.password)
    if not updated:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Impossible de définir le mot de passe")
    return {"message": "Mot de passe défini avec succès"}
