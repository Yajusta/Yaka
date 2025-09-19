"""Routeur pour la gestion des paramètres du tableau."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, UserRole
from ..schemas.board_settings import BoardSettingsResponse, BoardTitleUpdate
from ..services import board_settings as board_settings_service
from ..utils.dependencies import get_current_active_user

router = APIRouter(prefix="/board-settings", tags=["paramètres du tableau"])


def require_admin(current_user: User = Depends(get_current_active_user)):
    """Vérifier que l'utilisateur est administrateur."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux administrateurs")
    return current_user


@router.get("/", response_model=List[BoardSettingsResponse])
async def read_board_settings(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """Récupérer tous les paramètres du tableau (admin seulement)."""
    return board_settings_service.get_all_settings(db)


@router.get("/title")
async def get_board_title(db: Session = Depends(get_db)):
    """Récupérer le titre du tableau (accessible à tous)."""
    title = board_settings_service.get_board_title(db)
    return {"title": title}


@router.put("/title", response_model=BoardSettingsResponse)
async def update_board_title(
    title_update: BoardTitleUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)
):
    """Mettre à jour le titre du tableau (admin seulement)."""
    if not title_update.title or not title_update.title.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Le titre ne peut pas etre vide")

    return board_settings_service.set_board_title(db, title_update.title)


@router.get("/{setting_key}", response_model=BoardSettingsResponse)
async def read_board_setting(
    setting_key: str, db: Session = Depends(get_db), current_user: User = Depends(require_admin)
):
    """Récupérer un paramètre spécifique (admin seulement)."""
    if setting := board_settings_service.get_setting(db, setting_key):
        return setting
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paramètre non trouvé")


@router.put("/{setting_key}", response_model=BoardSettingsResponse)
async def update_board_setting(
    setting_key: str,
    setting_update: dict,  # Pour flexibilité, accepter un dict générique
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Mettre à jour un paramètre spécifique (admin seulement)."""
    allowed_keys = {"setting_value", "description"}
    if invalid_keys := set(setting_update.keys()) - allowed_keys:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Donnees invalides")

    setting_value = setting_update.get("setting_value")
    description = setting_update.get("description")

    if not setting_value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="setting_value est requis")

    return board_settings_service.create_or_update_setting(db, setting_key, setting_value, description)


@router.delete("/{setting_key}")
async def delete_board_setting(
    setting_key: str, db: Session = Depends(get_db), current_user: User = Depends(require_admin)
):
    """Supprimer un paramètre (admin seulement)."""
    if success := board_settings_service.delete_setting(db, setting_key):
        return {"message": "Paramètre supprimé avec succès"}
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paramètre non trouvé")
