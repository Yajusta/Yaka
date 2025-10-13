"""Router for managing card checklist items."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..multi_database import get_dynamic_db as get_db
from ..models import CardItem, User
from ..schemas.card_item import CardItemCreate, CardItemResponse, CardItemUpdate
from ..services import card as card_service
from ..services import card_item as card_item_service
from ..utils.dependencies import get_current_active_user
from ..utils.permissions import (
    ensure_can_create_card_item,
    ensure_can_delete_card_item,
    ensure_can_modify_card_item,
    ensure_can_toggle_card_item,
)

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
    """Create a new checklist item."""
    card = card_service.get_card(db, card_id=item.card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

    ensure_can_create_card_item(current_user, card)

    try:
        return card_item_service.create_item(db, item)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.put("/{item_id}", response_model=CardItemResponse)
async def update_item(
    item_id: int,
    item: CardItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update a checklist item.

    If only the 'is_done' field is modified, it's a toggle.
    Otherwise, it's a full modification.
    """
    existing_item = db.query(CardItem).filter(CardItem.id == item_id).first()
    if not existing_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    card = card_service.get_card(db, card_id=existing_item.card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

    # If only 'is_done' changes, it's a toggle (CONTRIBUTOR+)
    # Otherwise, it's a modification (EDITOR+)
    update_dict = item.model_dump(exclude_unset=True)
    if set(update_dict.keys()) == {"is_done"}:
        ensure_can_toggle_card_item(current_user, card)
    else:
        ensure_can_modify_card_item(current_user, card)

    if db_item := card_item_service.update_item(db, item_id, item):
        return db_item
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")


@router.delete("/{item_id}")
async def delete_item(
    item_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """Delete a checklist item."""
    existing_item = db.query(CardItem).filter(CardItem.id == item_id).first()
    if not existing_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    card = card_service.get_card(db, card_id=existing_item.card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

    ensure_can_delete_card_item(current_user, card)

    if ok := card_item_service.delete_item(db, item_id):
        return {"message": "Item deleted"}
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
