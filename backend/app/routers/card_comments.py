"""Routeur pour la gestion des commentaires des cartes."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas.card_comment import CardCommentCreate, CardCommentResponse, CardCommentUpdate
from ..schemas.card_history import CardHistoryCreate
from ..services import card as card_service
from ..services import card_comment as card_comment_service
from ..services.card_history import create_card_history_entry
from ..utils.dependencies import get_current_active_user
from ..utils.permissions import ensure_can_comment_on_card, ensure_can_delete_comment, ensure_can_edit_comment

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
    card = card_service.get_card(db, card_id=comment.card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carte non trouvée")

    ensure_can_comment_on_card(current_user, card)
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
    existing_comment = card_comment_service.get_comment_by_id(db, comment_id)
    if not existing_comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commentaire non trouvé")

    # Vérifier que l'utilisateur peut modifier ce commentaire spécifique
    ensure_can_edit_comment(current_user, existing_comment)

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

        # Vérifier que l'utilisateur peut supprimer ce commentaire spécifique
        ensure_can_delete_comment(current_user, db_comment)

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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
