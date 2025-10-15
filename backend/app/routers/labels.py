"""Routeur pour la gestion des libellés."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..multi_database import get_dynamic_db as get_db
from ..models import User
from ..schemas import LabelCreate, LabelResponse, LabelUpdate
from ..services import label as label_service
from ..utils.dependencies import get_current_active_user, require_admin

router = APIRouter(prefix="/labels", tags=["libellés"])


@router.get("/", response_model=List[LabelResponse])
async def read_labels(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Récupérer la liste des libellés."""
    return label_service.get_labels(db, skip=skip, limit=limit)


@router.post("/", response_model=LabelResponse)
async def create_label(label: LabelCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """Créer un nouveau libellé (Admin uniquement)."""
    if label is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Données invalides pour la création du libellé"
        )
    try:
        db_label = label_service.get_label_by_name(db, name=label.name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if db_label:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Un libellé avec ce nom existe déjà")
    try:
        return label_service.create_label(db=db, label=label, created_by=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{label_id}", response_model=LabelResponse)
async def read_label(
    label_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """Récupérer un libellé par son ID."""
    db_label = label_service.get_label(db, label_id=label_id)
    if db_label is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Libellé non trouvé")
    return db_label


@router.put("/{label_id}", response_model=LabelResponse)
async def update_label(
    label_id: int,
    label_update: LabelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Mettre à jour un libellé (Admin uniquement)."""
    try:
        label_id = int(label_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Identifiant de libellé invalide"
        ) from exc
    if label_update is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Données invalides pour la mise à jour du libellé"
        )
    try:
        db_label = label_service.update_label(db, label_id=label_id, label_update=label_update)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if db_label is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Libellé non trouvé")
    return db_label


@router.delete("/{label_id}")
async def delete_label(label_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """Supprimer un libellé (Admin uniquement)."""
    if success := label_service.delete_label(db, label_id=label_id):
        return {"message": "Libellé supprimé avec succès"}
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Libellé non trouvé")
