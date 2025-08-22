"""Routeur pour la gestion des éléments de checklist des cartes."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..utils.dependencies import get_current_active_user
from ..models import User
from ..schemas.card_item import CardItemResponse, CardItemCreate, CardItemUpdate
from ..services import card_item as card_item_service


router = APIRouter(prefix="/card-items", tags=["card-items"])


@router.get("/card/{card_id}", response_model=List[CardItemResponse])
async def list_items(
    card_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    return card_item_service.get_items_for_card(db, card_id)


@router.post("/", response_model=CardItemResponse)
async def create_item(
    item: CardItemCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    try:
        return card_item_service.create_item(db, item)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{item_id}", response_model=CardItemResponse)
async def update_item(
    item_id: int,
    item: CardItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    db_item = card_item_service.update_item(db, item_id, item)
    if not db_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Élément non trouvé")
    return db_item


@router.delete("/{item_id}")
async def delete_item(
    item_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    ok = card_item_service.delete_item(db, item_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Élément non trouvé")
    return {"message": "Élément supprimé"}
