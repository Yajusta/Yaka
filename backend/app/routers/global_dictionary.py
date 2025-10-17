"""Router for global dictionary management."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..multi_database import get_dynamic_db as get_db
from ..models import User
from ..schemas import GlobalDictionaryCreate, GlobalDictionaryResponse, GlobalDictionaryUpdate
from ..services import global_dictionary as global_dictionary_service
from ..utils.dependencies import get_current_active_user, require_admin

router = APIRouter(prefix="/global-dictionary", tags=["global-dictionary"])


@router.get("/", response_model=List[GlobalDictionaryResponse])
async def read_entries(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get the list of global dictionary entries (accessible to all authenticated users)."""
    return global_dictionary_service.get_entries(db, skip=skip, limit=limit)


@router.post("/", response_model=GlobalDictionaryResponse)
async def create_entry(
    entry: GlobalDictionaryCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)
):
    """Create a new global dictionary entry (Admin only)."""
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid data for creating dictionary entry",
        )
    try:
        db_entry = global_dictionary_service.get_entry_by_term(db, term=entry.term)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if db_entry:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An entry with this term already exists")
    try:
        return global_dictionary_service.create_entry(db=db, entry=entry)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{entry_id}", response_model=GlobalDictionaryResponse)
async def read_entry(
    entry_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """Get a global dictionary entry by its ID."""
    db_entry = global_dictionary_service.get_entry(db, entry_id=entry_id)
    if db_entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dictionary entry not found")
    return db_entry


@router.put("/{entry_id}", response_model=GlobalDictionaryResponse)
async def update_entry(
    entry_id: int,
    entry_update: GlobalDictionaryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Update a global dictionary entry (Admin only)."""
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
    try:
        db_entry = global_dictionary_service.update_entry(db, entry_id=entry_id, entry_update=entry_update)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if db_entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dictionary entry not found")
    return db_entry


@router.delete("/{entry_id}")
async def delete_entry(
    entry_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)
):
    """Delete a global dictionary entry (Admin only)."""
    if success := global_dictionary_service.delete_entry(db, entry_id=entry_id):
        return {"message": "Dictionary entry deleted successfully"}
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dictionary entry not found")

