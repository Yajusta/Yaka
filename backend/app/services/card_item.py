"""Service pour la gestion des éléments de checklist des cartes."""

from typing import List, Optional

from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import Card, CardItem
from ..schemas.card_item import CardItemCreate, CardItemUpdate


def get_items_for_card(db: Session, card_id: int) -> List[CardItem]:
    return db.query(CardItem).filter(CardItem.card_id == card_id).order_by(CardItem.position).all()


def create_item(db: Session, item: CardItemCreate) -> CardItem:
    # Ensure card exists
    card = db.query(Card).filter(Card.id == item.card_id).first()
    if not card:
        raise ValueError("Carte introuvable")

    # Determine position if not provided, with retry on IntegrityError
    max_retries = 5
    for attempt in range(max_retries):
        try:
            # Start transaction with SERIALIZABLE isolation level
            if item.position is None:
                if db.bind and db.bind.dialect.name != "sqlite":
                    db.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))

                max_pos = db.query(func.max(CardItem.position)).filter(CardItem.card_id == item.card_id).scalar()
                position = (max_pos or 0) + 1
            else:
                position = item.position
                # shift existing items at or after position
                db.query(CardItem).filter(CardItem.card_id == item.card_id, CardItem.position >= position).update(
                    {CardItem.position: CardItem.position + 1}, synchronize_session="evaluate"
                )

            db_item = CardItem(
                card_id=item.card_id,
                text=item.text,
                is_done=item.is_done,
                position=position,
            )
            db.add(db_item)
            db.commit()
            db.refresh(db_item)
            return db_item
        except IntegrityError as e:
            db.rollback()
            if item.position is not None:
                raise
            # For auto-position, continue retrying
            if attempt == max_retries - 1:
                raise ValueError(f"Could not assign unique position after {max_retries} retries") from e
    raise ValueError("Could not assign unique position after several retries")


def update_item(db: Session, item_id: int, item_update: CardItemUpdate) -> Optional[CardItem]:
    db_item = db.query(CardItem).filter(CardItem.id == item_id).first()
    if not db_item:
        return None

    data = item_update.model_dump(exclude_unset=True)
    new_position = data.pop("position", None)
    for k, v in data.items():
        if k not in CardItem.PROTECTED_FIELDS:
            setattr(db_item, k, v)

    if new_position is not None and new_position != db_item.position:
        # Reorder within same card
        if new_position > db_item.position:
            db.query(CardItem).filter(
                CardItem.card_id == db_item.card_id,
                CardItem.position > db_item.position,
                CardItem.position <= new_position,
                CardItem.id != db_item.id,
            ).update({CardItem.position: CardItem.position - 1}, synchronize_session="evaluate")
        else:
            db.query(CardItem).filter(
                CardItem.card_id == db_item.card_id,
                CardItem.position >= new_position,
                CardItem.position < db_item.position,
                CardItem.id != db_item.id,
            ).update({CardItem.position: CardItem.position + 1}, synchronize_session="evaluate")
        db_item.position = new_position

    db.commit()
    db.refresh(db_item)
    return db_item


def delete_item(db: Session, item_id: int) -> bool:
    db_item = db.query(CardItem).filter(CardItem.id == item_id).first()
    if not db_item:
        return False
    card_id = db_item.card_id
    removed_pos = db_item.position
    db.delete(db_item)
    db.commit()
    # compact positions
    db.query(CardItem).filter(CardItem.card_id == card_id, CardItem.position > removed_pos).update(
        {CardItem.position: CardItem.position - 1}, synchronize_session="evaluate"
    )
    db.commit()
    return True
