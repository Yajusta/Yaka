"""Service pour la gestion des commentaires des cartes."""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from ..models import Card, CardComment, User as UserModel
from ..schemas.card_comment import CardCommentCreate, CardCommentUpdate


def get_comments_for_card(db: Session, card_id: int) -> List[CardComment]:
    """Récupère tous les commentaires non supprimés d'une carte triés par date décroissante."""
    return (
        db.query(CardComment)
        .options(joinedload(CardComment.user))
        .filter(and_(CardComment.card_id == card_id, CardComment.is_deleted == False))
        .order_by(CardComment.created_at.desc())
        .all()
    )


def create_comment(db: Session, comment: CardCommentCreate, user_id: int) -> CardComment:
    """Crée un nouveau commentaire pour une carte."""
    # Ensure card exists
    card = db.query(Card).filter(Card.id == comment.card_id).first()
    if not card:
        raise ValueError("Carte introuvable")

    # Ensure user exists
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise ValueError("Utilisateur introuvable")

    db_comment = CardComment(card_id=comment.card_id, user_id=user_id, comment=comment.comment)
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)

    # Recharger avec la relation user pour s'assurer que les données sont disponibles
    result = (
        db.query(CardComment).options(joinedload(CardComment.user)).filter(CardComment.id == db_comment.id).first()
    )

    if result is None:
        raise ValueError("Erreur lors de la création du commentaire")

    return result


def update_comment(
    db: Session, comment_id: int, comment_update: CardCommentUpdate, user_id: int
) -> Optional[CardComment]:
    """Met à jour un commentaire."""
    db_comment = db.query(CardComment).filter(CardComment.id == comment_id).first()
    if not db_comment:
        raise ValueError("Commentaire introuvable")

    # Ensure the user owns the comment
    if db_comment.user_id != user_id:
        raise ValueError("Vous ne pouvez modifier que vos propres commentaires")

    # Update only if not deleted
    if db_comment.is_deleted:
        raise ValueError("Impossible de modifier un commentaire supprimé")

    update_data = comment_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_comment, key, value)

    db.commit()

    # Recharger avec la relation user pour s'assurer que les données sont disponibles
    result = (
        db.query(CardComment).options(joinedload(CardComment.user)).filter(CardComment.id == db_comment.id).first()
    )

    if result is None:
        raise ValueError("Erreur lors de la mise à jour du commentaire")

    return result


def delete_comment(db: Session, comment_id: int, user_id: int) -> bool:
    """Supprime logiquement un commentaire (soft delete)."""
    db_comment = db.query(CardComment).filter(CardComment.id == comment_id).first()
    if not db_comment:
        return False

    # Ensure the user owns the comment
    if db_comment.user_id != user_id:
        raise ValueError("Vous ne pouvez supprimer que vos propres commentaires")

    # Mark as deleted
    db_comment.is_deleted = True
    db.commit()
    return True


def get_comment_by_id(db: Session, comment_id: int) -> Optional[CardComment]:
    """Récupère un commentaire par son ID si non supprimé."""
    return (
        db.query(CardComment)
        .options(joinedload(CardComment.user))
        .filter(and_(CardComment.id == comment_id, CardComment.is_deleted == False))
        .first()
    )
