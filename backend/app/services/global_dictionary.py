"""Service for managing global dictionary entries."""

from typing import List, Optional

from sqlalchemy.orm import Session

from ..models import GlobalDictionary
from ..schemas import GlobalDictionaryCreate, GlobalDictionaryUpdate


def get_entry(db: Session, entry_id: int) -> Optional[GlobalDictionary]:
    """Get a global dictionary entry by ID."""
    return db.query(GlobalDictionary).filter(GlobalDictionary.id == entry_id).first()


def get_entries(db: Session, skip: int = 0, limit: int = 100) -> List[GlobalDictionary]:
    """Get a list of global dictionary entries."""
    return db.query(GlobalDictionary).order_by(GlobalDictionary.term).offset(skip).limit(limit).all()


def get_entry_by_term(db: Session, term: str) -> Optional[GlobalDictionary]:
    """Get a global dictionary entry by term."""
    return db.query(GlobalDictionary).filter(GlobalDictionary.term == term).first()


def create_entry(db: Session, entry: GlobalDictionaryCreate) -> GlobalDictionary:
    """Create a new global dictionary entry."""
    db_entry = GlobalDictionary(term=entry.term, definition=entry.definition)
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry


def update_entry(db: Session, entry_id: int, entry_update: GlobalDictionaryUpdate) -> Optional[GlobalDictionary]:
    """Update a global dictionary entry."""
    db_entry = get_entry(db, entry_id)
    if not db_entry:
        return None

    update_data = entry_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_entry, field, value)

    db.commit()
    db.refresh(db_entry)
    return db_entry


def delete_entry(db: Session, entry_id: int) -> bool:
    """Delete a global dictionary entry."""
    db_entry = get_entry(db, entry_id)
    if not db_entry:
        return False

    db.delete(db_entry)
    db.commit()
    return True

