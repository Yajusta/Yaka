"""Routeur pour la gestion des libellés."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas import LabelCreate, LabelUpdate, LabelResponse
from ..services import label as label_service
from ..utils.dependencies import require_admin, get_current_active_user
from ..models import User

router = APIRouter(prefix="/labels", tags=["libellés"])


@router.get("/", response_model=List[LabelResponse])
async def read_labels(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Récupérer la liste des libellés."""
    labels = label_service.get_labels(db, skip=skip, limit=limit)
    return labels


@router.post("/", response_model=LabelResponse)
async def create_label(
    label: LabelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Créer un nouveau libellé (Admin uniquement)."""
    db_label = label_service.get_label_by_name(db, nom=label.nom)
    if db_label:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un libellé avec ce nom existe déjà"
        )
    return label_service.create_label(db=db, label=label, created_by=current_user.id)


@router.get("/{label_id}", response_model=LabelResponse)
async def read_label(
    label_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Récupérer un libellé par son ID."""
    db_label = label_service.get_label(db, label_id=label_id)
    if db_label is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Libellé non trouvé"
        )
    return db_label


@router.put("/{label_id}", response_model=LabelResponse)
async def update_label(
    label_id: int,
    label_update: LabelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Mettre à jour un libellé (Admin uniquement)."""
    db_label = label_service.update_label(db, label_id=label_id, label_update=label_update)
    if db_label is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Libellé non trouvé"
        )
    return db_label


@router.delete("/{label_id}")
async def delete_label(
    label_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Supprimer un libellé (Admin uniquement)."""
    success = label_service.delete_label(db, label_id=label_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Libellé non trouvé"
        )
    return {"message": "Libellé supprimé avec succès"}

