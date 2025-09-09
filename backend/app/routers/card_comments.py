"""Routeur pour la gestion des commentaires des cartes."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..utils.dependencies import get_current_active_user
from ..models import User
from ..schemas.card_comment import CardCommentResponse, CardCommentCreate, CardCommentUpdate
from ..services import card_comment as card_comment_service
from ..services.card_history import create_card_history_entry
from ..schemas.card_history import CardHistoryCreate


router = APIRouter(prefix="/card-comments", tags=["card-comments"])


@router.get("/card/{card_id}", response_model=List[CardCommentResponse])
async def list_comments(
    card_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Récupérer tous les commentaires non supprimés d'une carte."""
    return card_comment_service.get_comments_for_card(db, card_id)


@router.post("/", response_model=CardCommentResponse)
async def create_comment(
    comment: CardCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Créer un nouveau commentaire pour une carte."""
    try:
        db_comment = card_comment_service.create_comment(db, comment, current_user.id)

        # Historise l'événement
        history_entry = CardHistoryCreate(
            card_id=comment.card_id, user_id=current_user.id, action="comment_added", description="Commentaire ajouté"
        )
        create_card_history_entry(db, history_entry)

        db.refresh(db_comment)
        return db_comment
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.put("/{comment_id}", response_model=CardCommentResponse)
async def update_comment(
    comment_id: int,
    comment: CardCommentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Mettre à jour un commentaire."""
    try:
        db_comment = card_comment_service.update_comment(db, comment_id, comment, current_user.id)

        # La fonction update_comment peut retourner None, mais elle lève une exception si échec
        # On sait donc que si on arrive ici, db_comment n'est pas None
        assert db_comment is not None, "Commentaire devrait exister après mise à jour"

        # Historise l'événement
        history_entry = CardHistoryCreate(
            card_id=db_comment.card_id,
            user_id=current_user.id,
            action="comment_updated",
            description="Commentaire modifié",
        )
        create_card_history_entry(db, history_entry)

        return db_comment
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.delete("/{comment_id}")
async def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Supprimer logiquement un commentaire."""
    try:
        # Get comment info before deleting
        db_comment = card_comment_service.get_comment_by_id(db, comment_id)
        if not db_comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commentaire non trouvé")

        # À ce point, db_comment n'est pas None, pas besoin de type: ignore
        card_id: int = db_comment.card_id

        ok = card_comment_service.delete_comment(db, comment_id, current_user.id)

        if not ok:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commentaire non trouvé")

        # Historise l'événement
        history_entry = CardHistoryCreate(
            card_id=card_id,
            user_id=current_user.id,
            action="comment_deleted",
            description="Commentaire supprimé",
        )
        create_card_history_entry(db, history_entry)

        return {"message": "Commentaire supprimé"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
