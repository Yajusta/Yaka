"""Router for personal dictionary management."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..multi_database import get_dynamic_db as get_db
from ..models import User, UserRole
from ..schemas import PersonalDictionaryCreate, PersonalDictionaryResponse, PersonalDictionaryUpdate
from ..services import personal_dictionary as personal_dictionary_service
from ..utils.dependencies import get_current_active_user

router = APIRouter(prefix="/personal-dictionary", tags=["personal-dictionary"])


def require_editor_or_above(current_user: User = Depends(get_current_active_user)) -> User:
    """Require user to be at least an EDITOR."""
    editor_roles = [UserRole.EDITOR, UserRole.SUPERVISOR, UserRole.ADMIN]
    if current_user.role not in editor_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Editor role or higher required.",
        )
    return current_user


@router.get("/", response_model=List[PersonalDictionaryResponse])
async def read_entries(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor_or_above),
):
    """Get the list of personal dictionary entries for the current user."""
    return personal_dictionary_service.get_entries_by_user(db, user_id=current_user.id, skip=skip, limit=limit)


@router.post("/", response_model=PersonalDictionaryResponse)
async def create_entry(
    entry: PersonalDictionaryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor_or_above),
):
    """Create a new personal dictionary entry for the current user."""
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid data for creating dictionary entry",
        )
    try:
        db_entry = personal_dictionary_service.get_entry_by_user_and_term(
            db, user_id=current_user.id, term=entry.term
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if db_entry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You already have an entry with this term"
        )
    try:
        return personal_dictionary_service.create_entry(db=db, entry=entry, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{entry_id}", response_model=PersonalDictionaryResponse)
async def read_entry(
    entry_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_editor_or_above)
):
    """Get a personal dictionary entry by its ID (only if it belongs to the current user)."""
    db_entry = personal_dictionary_service.get_entry(db, entry_id=entry_id)
    if db_entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dictionary entry not found")
    
    # Check if the entry belongs to the current user
    if db_entry.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You can only access your own dictionary entries"
        )
    
    return db_entry


@router.put("/{entry_id}", response_model=PersonalDictionaryResponse)
async def update_entry(
    entry_id: int,
    entry_update: PersonalDictionaryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor_or_above),
):
    """Update a personal dictionary entry (only if it belongs to the current user)."""
    try:
        entry_id = int(entry_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid dictionary entry ID"
        ) from exc
    if entry_update is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid data for updating dictionary entry",
        )
    
    # Check if the entry exists and belongs to the current user
    db_entry = personal_dictionary_service.get_entry(db, entry_id=entry_id)
    if db_entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dictionary entry not found")
    
    if db_entry.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You can only update your own dictionary entries"
        )
    
    try:
        db_entry = personal_dictionary_service.update_entry(db, entry_id=entry_id, entry_update=entry_update)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if db_entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dictionary entry not found")
    return db_entry


@router.delete("/{entry_id}")
async def delete_entry(
    entry_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_editor_or_above)
):
    """Delete a personal dictionary entry (only if it belongs to the current user)."""
    # Check if the entry exists and belongs to the current user
    db_entry = personal_dictionary_service.get_entry(db, entry_id=entry_id)
    if db_entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dictionary entry not found")
    
    if db_entry.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete your own dictionary entries"
        )
    
    if success := personal_dictionary_service.delete_entry(db, entry_id=entry_id):
        return {"message": "Dictionary entry deleted successfully"}
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dictionary entry not found")

