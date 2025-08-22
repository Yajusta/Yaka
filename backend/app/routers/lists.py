"""Routeur pour la gestion des listes Kanban."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas import (
    KanbanListCreate, 
    KanbanListUpdate, 
    KanbanListResponse, 
    ListDeletionRequest,
    ListReorderRequest
)
from ..services import kanban_list as list_service
from ..utils.dependencies import get_current_active_user, require_admin
from ..models import User

router = APIRouter(prefix="/lists", tags=["listes"])


@router.get("/", response_model=List[KanbanListResponse])
async def read_lists(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Récupérer toutes les listes ordonnées par ordre d'affichage."""
    lists = list_service.get_lists(db)
    return lists


@router.post("/", response_model=KanbanListResponse)
async def create_list(
    list_data: KanbanListCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Créer une nouvelle liste (admin seulement)."""
    try:
        new_list = list_service.create_list(db=db, list_data=list_data)
        return new_list
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne lors de la création de la liste"
        )


@router.get("/{list_id}", response_model=KanbanListResponse)
async def read_list(
    list_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Récupérer une liste par son ID."""
    db_list = list_service.get_list(db, list_id=list_id)
    if db_list is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Liste non trouvée"
        )
    return db_list


@router.put("/{list_id}", response_model=KanbanListResponse)
async def update_list(
    list_id: int,
    list_update: KanbanListUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Mettre à jour une liste (admin seulement)."""
    # Validation de l'ID
    if list_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="L'ID de la liste doit être un entier positif"
        )
    
    try:
        db_list = list_service.update_list(db, list_id=list_id, list_data=list_update)
        if db_list is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Liste avec l'ID {list_id} non trouvée"
            )
        return db_list
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne lors de la mise à jour de la liste"
        )


@router.delete("/{list_id}")
async def delete_list(
    list_id: int,
    deletion_request: ListDeletionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Supprimer une liste après avoir déplacé ses cartes (admin seulement)."""
    # Validation de l'ID
    if list_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="L'ID de la liste doit être un entier positif"
        )
    
    try:
        success = list_service.delete_list(
            db, 
            list_id=list_id, 
            target_list_id=deletion_request.target_list_id
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Liste avec l'ID {list_id} non trouvée"
            )
        return {"message": "Liste supprimée avec succès"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne lors de la suppression de la liste"
        )


@router.get("/{list_id}/cards-count")
async def get_list_cards_count(
    list_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Récupérer le nombre de cartes dans une liste."""
    # Validation de l'ID
    if list_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="L'ID de la liste doit être un entier positif"
        )
    
    try:
        kanban_list, cards_count = list_service.get_list_with_cards_count(db, list_id=list_id)
        if kanban_list is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Liste avec l'ID {list_id} non trouvée"
            )
        return {
            "list_id": list_id,
            "list_name": kanban_list.name,
            "cards_count": cards_count
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne lors de la récupération du nombre de cartes"
        )


@router.post("/reorder")
async def reorder_lists(
    reorder_request: ListReorderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Réorganiser l'ordre des listes (admin seulement)."""
    try:
        success = list_service.reorder_lists(db, list_orders=reorder_request.list_orders)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Erreur lors de la réorganisation des listes"
            )
        return {"message": "Listes réorganisées avec succès"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne lors de la réorganisation des listes"
        )