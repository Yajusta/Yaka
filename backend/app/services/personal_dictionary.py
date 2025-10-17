"""Service for managing personal dictionary entries."""

from typing import List, Optional

from sqlalchemy.orm import Session

from ..models import PersonalDictionary
from ..schemas import PersonalDictionaryCreate, PersonalDictionaryUpdate


def get_entry(db: Session, entry_id: int) -> Optional[PersonalDictionary]:
    """Get a personal dictionary entry by ID."""
    return db.query(PersonalDictionary).filter(PersonalDictionary.id == entry_id).first()


def get_entries_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[PersonalDictionary]:
    """Get a list of personal dictionary entries for a specific user."""
    return (
        db.query(PersonalDictionary)
        .filter(PersonalDictionary.user_id == user_id)
        .order_by(PersonalDictionary.term)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_entry_by_user_and_term(db: Session, user_id: int, term: str) -> Optional[PersonalDictionary]:
    """Get a personal dictionary entry by user ID and term."""
    return (
        db.query(PersonalDictionary)
        .filter(PersonalDictionary.user_id == user_id, PersonalDictionary.term == term)
        .first()
    )


def create_entry(db: Session, entry: PersonalDictionaryCreate, user_id: int) -> PersonalDictionary:
    """Create a new personal dictionary entry."""
    db_entry = PersonalDictionary(user_id=user_id, term=entry.term, definition=entry.definition)
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry


def update_entry(db: Session, entry_id: int, entry_update: PersonalDictionaryUpdate) -> Optional[PersonalDictionary]:
    """Update a personal dictionary entry."""
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
    """Delete a personal dictionary entry."""
    db_entry = get_entry(db, entry_id)
    if not db_entry:
        return False

    db.delete(db_entry)
    db.commit()
    return True

