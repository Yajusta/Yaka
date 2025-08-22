"""Service pour la gestion des cartes."""

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from typing import Optional, List
from ..models import Card, Label, KanbanList
from ..schemas import CardCreate, CardUpdate, CardListUpdate, CardFilter, CardMoveRequest, BulkCardMoveRequest


def get_card(db: Session, card_id: int) -> Optional[Card]:
    """Récupérer une carte par son ID."""
    return db.query(Card).filter(Card.id == card_id).first()


def get_cards(db: Session, filters: CardFilter, skip: int = 0, limit: int = 100) -> List[Card]:
    """Récupérer une liste de cartes avec filtres."""
    query = db.query(Card)

    # Filtrer les cartes archivées si nécessaire
    if not filters.include_archived:
        query = query.filter(Card.is_archived == False)

    # Filtrer par liste
    if filters.list_id:
        query = query.filter(Card.list_id == filters.list_id)

    # Filtrer par assigné
    if filters.assignee_id:
        query = query.filter(Card.assignee_id == filters.assignee_id)

    # Filtrer par priorité
    if filters.priorite:
        query = query.filter(Card.priorite == filters.priorite)

    # Filtrer par libellé
    if filters.label_id:
        query = query.join(Card.labels).filter(Label.id == filters.label_id)

    # Recherche textuelle
    if filters.search:
        search_term = f"%{filters.search}%"
        query = query.filter(or_(Card.titre.ilike(search_term), Card.description.ilike(search_term)))

    # Trier par position dans la liste, puis par date de création
    query = query.order_by(Card.position, Card.created_at)

    return query.offset(skip).limit(limit).all()


def get_archived_cards(db: Session, skip: int = 0, limit: int = 100) -> List[Card]:
    """Récupérer les cartes archivées."""
    return db.query(Card).filter(Card.is_archived == True).offset(skip).limit(limit).all()


def create_card(db: Session, card: CardCreate, created_by: int) -> Card:
    """Créer une nouvelle carte.

    Comportement spécial: si ``card.list_id`` vaut -1, la carte sera automatiquement
    affectée à la liste valide ayant l'order le plus bas.
    """
    # Résoudre la liste cible
    target_list_id = card.list_id
    if target_list_id == -1:
        lowest_list = db.query(KanbanList).order_by(KanbanList.order.asc()).first()
        if not lowest_list:
            # Aucune liste valide n'existe
            raise ValueError("Aucune liste valide n'est disponible pour créer la carte")
        target_list_id = lowest_list.id

    # Déterminer la position de la nouvelle carte
    if card.position is not None:
        # Position spécifiée - décaler les autres cartes
        _shift_positions_for_insertion(db, target_list_id, card.position)
        position = card.position
    else:
        # Pas de position spécifiée - ajouter à la fin
        max_position = db.query(func.max(Card.position)).filter(Card.list_id == target_list_id).scalar()
        position = (max_position or 0) + 1

    db_card = Card(
        titre=card.titre,
        description=card.description,
        date_echeance=card.date_echeance,
        priorite=card.priorite,
        list_id=target_list_id,
        position=position,
        assignee_id=card.assignee_id,
        created_by=created_by,
    )

    # Ajouter les libellés
    if card.label_ids:
        labels = db.query(Label).filter(Label.id.in_(card.label_ids)).all()
        db_card.labels = labels

    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    return db_card


def update_card(db: Session, card_id: int, card_update: CardUpdate) -> Optional[Card]:
    """Mettre à jour une carte."""
    db_card = get_card(db, card_id)
    if not db_card:
        return None

    update_data = card_update.dict(exclude_unset=True)

    # Gérer les libellés séparément
    label_ids = update_data.pop("label_ids", None)

    # Si on reçoit list_id = -1 lors d'une mise à jour, le résoudre vers la liste au plus petit order
    if "list_id" in update_data and update_data["list_id"] == -1:
        lowest_list = db.query(KanbanList).order_by(KanbanList.order.asc()).first()
        if not lowest_list:
            raise ValueError("Aucune liste valide n'est disponible pour mettre à jour la carte")
        update_data["list_id"] = lowest_list.id

    for field, value in update_data.items():
        setattr(db_card, field, value)

    # Mettre à jour les libellés si fournis
    if label_ids is not None:
        labels = db.query(Label).filter(Label.id.in_(label_ids)).all()
        db_card.labels = labels

    db.commit()
    db.refresh(db_card)
    return db_card


def update_card_list(db: Session, card_id: int, list_update: CardListUpdate) -> Optional[Card]:
    """Mettre à jour la liste d'une carte."""
    db_card = get_card(db, card_id)
    if not db_card:
        return None

    # Gérer le cas spécial list_id = -1
    target_list_id = list_update.list_id
    if target_list_id == -1:
        lowest_list = db.query(KanbanList).order_by(KanbanList.order.asc()).first()
        if not lowest_list:
            return None
        target_list_id = lowest_list.id

    db_card.list_id = target_list_id
    db.commit()
    db.refresh(db_card)
    return db_card


def archive_card(db: Session, card_id: int) -> Optional[Card]:
    """Archiver une carte."""
    db_card = get_card(db, card_id)
    if not db_card:
        return None

    db_card.is_archived = True
    db.commit()
    db.refresh(db_card)
    return db_card


def unarchive_card(db: Session, card_id: int) -> Optional[Card]:
    """Désarchiver une carte."""
    db_card = get_card(db, card_id)
    if not db_card:
        return None

    db_card.is_archived = False
    db.commit()
    db.refresh(db_card)
    return db_card


def delete_card(db: Session, card_id: int) -> bool:
    """Supprimer définitivement une carte."""
    db_card = get_card(db, card_id)
    if not db_card:
        return False

    db.delete(db_card)
    db.commit()
    return True


def move_card(db: Session, card_id: int, move_request: CardMoveRequest) -> Optional[Card]:
    """Déplacer une carte entre listes avec gestion de position."""
    db_card = get_card(db, card_id)
    if not db_card:
        return None

    # Vérifier que la carte est actuellement dans la liste source
    if db_card.list_id != move_request.source_list_id:
        return None

    old_list_id = db_card.list_id
    old_position = db_card.position
    new_list_id = move_request.target_list_id

    # Si on déplace dans la même liste, on réorganise les positions
    if old_list_id == new_list_id:
        # Réorganisation dans la même liste - utiliser la position fournie ou mettre à la fin
        target_position = getattr(move_request, "position", None)
        if target_position is None:
            # Pas de position spécifiée, mettre à la fin
            max_position = db.query(func.max(Card.position)).filter(Card.list_id == new_list_id).scalar()
            target_position = (max_position or 0) + 1

        _reorder_cards_in_same_list(db, card_id, old_position, target_position, new_list_id)
        db_card.position = target_position
    else:
        # Déplacement vers une autre liste
        # 1. Compacter les positions dans l'ancienne liste
        _compact_positions_after_removal(db, old_list_id, old_position)

        # 2. Déterminer la position dans la nouvelle liste
        target_position = getattr(move_request, "position", None)
        if target_position is None:
            # Pas de position spécifiée, mettre à la fin
            max_position = db.query(func.max(Card.position)).filter(Card.list_id == new_list_id).scalar()
            target_position = (max_position or 0) + 1
        else:
            # Décaler les cartes existantes dans la liste de destination
            _shift_positions_for_insertion(db, new_list_id, target_position)

        # 3. Mettre à jour la carte
        db_card.list_id = new_list_id
        db_card.position = target_position

    db.commit()
    db.refresh(db_card)
    return db_card


def _reorder_cards_in_same_list(db: Session, card_id: int, old_position: int, new_position: int, list_id: int):
    """Réorganiser les positions des cartes dans la même liste."""
    if old_position == new_position:
        return

    if new_position > old_position:
        # Déplacer vers le bas : décaler les cartes entre old_position+1 et new_position vers le haut
        db.query(Card).filter(
            Card.list_id == list_id, Card.position > old_position, Card.position <= new_position, Card.id != card_id
        ).update({Card.position: Card.position - 1})
    else:
        # Déplacer vers le haut : décaler les cartes entre new_position et old_position-1 vers le bas
        db.query(Card).filter(
            Card.list_id == list_id, Card.position >= new_position, Card.position < old_position, Card.id != card_id
        ).update({Card.position: Card.position + 1})


def _compact_positions_after_removal(db: Session, list_id: int, removed_position: int):
    """Compacter les positions après suppression d'une carte."""
    db.query(Card).filter(Card.list_id == list_id, Card.position > removed_position).update(
        {Card.position: Card.position - 1}
    )


def _shift_positions_for_insertion(db: Session, list_id: int, insert_position: int):
    """Décaler les positions pour faire de la place à une nouvelle carte."""
    db.query(Card).filter(Card.list_id == list_id, Card.position >= insert_position).update(
        {Card.position: Card.position + 1}
    )


def bulk_move_cards(db: Session, bulk_move_request: BulkCardMoveRequest) -> List[Card]:
    """Déplacer plusieurs cartes vers une liste de destination."""
    cards = db.query(Card).filter(Card.id.in_(bulk_move_request.card_ids)).all()

    if not cards:
        return []

    # Obtenir la position maximale dans la liste de destination
    max_position = db.query(func.max(Card.position)).filter(Card.list_id == bulk_move_request.target_list_id).scalar()
    next_position = (max_position or 0) + 1

    # Déplacer toutes les cartes vers la liste de destination
    for i, card in enumerate(cards):
        card.list_id = bulk_move_request.target_list_id
        card.position = next_position + i

    db.commit()

    # Rafraîchir toutes les cartes
    for card in cards:
        db.refresh(card)

    return cards
