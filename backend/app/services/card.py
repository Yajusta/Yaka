"""Service pour la gestion des cartes."""

from typing import List, Optional

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload

from ..models import Card, CardComment, CardPriority, KanbanList, Label, User
from ..schemas import (
    BulkCardMoveRequest,
    CardCreate,
    CardFilter,
    CardHistoryCreate,
    CardListUpdate,
    CardMoveRequest,
    CardUpdate,
)
from . import card_history as card_history_service


def get_card(db: Session, card_id: int) -> Optional[Card]:
    """Récupérer une carte par son ID avec ses relations."""
    card = db.query(Card).filter(Card.id == card_id).first()
    if card:
        # Filtrer les commentaires pour ne garder que les non supprimés
        card.comments = [comment for comment in card.comments if not comment.is_deleted]
    return card


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
    if filters.priority:
        query = query.filter(Card.priority == filters.priority)

    # Filtrer par libellé
    if filters.label_id:
        query = query.join(Card.labels).filter(Label.id == filters.label_id)

    # Recherche textuelle
    if filters.search:
        search_term = f"%{filters.search}%"
        query = query.filter(or_(Card.title.ilike(search_term), Card.description.ilike(search_term)))

    # Trier par position dans la liste, puis par date de création
    query = query.order_by(Card.position, Card.created_at)

    cards = query.options(joinedload(Card.comments).joinedload(CardComment.user)).offset(skip).limit(limit).all()

    # Filtrer les commentaires pour ne garder que les non supprimés
    for card in cards:
        card.comments = [comment for comment in card.comments if not comment.is_deleted]

    return cards


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
        if lowest_list := db.query(KanbanList).order_by(KanbanList.order.asc()).first():
            target_list_id = lowest_list.id

        else:
            # Aucune liste valide n'existe
            raise ValueError("Aucune liste valide n'est disponible pour créer la carte")
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
        title=card.title,
        description=card.description,
        due_date=card.due_date,
        priority=card.priority,
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

    # Créer une entrée d'historique pour la création de la carte
    try:
        history_entry = CardHistoryCreate(
            card_id=db_card.id, user_id=created_by, action="create", description=f"Carte « {db_card.title} » créée"
        )
        card_history_service.create_card_history_entry(db, history_entry)
    except Exception as e:
        # Ne pas échouer la création de la carte si l'historique échoue
        print(f"Warning: Failed to create history entry for card creation: {e}")

    return db_card


def update_card(
    db: Session, card_id: int, card_update: CardUpdate, updated_by: Optional[int] = None
) -> Optional[Card]:
    """Mettre à jour une carte."""
    db_card = get_card(db, card_id)
    if not db_card:
        return None

    update_data = card_update.model_dump(exclude_unset=True)

    # Gérer les libellés séparément
    label_ids = update_data.pop("label_ids", None)

    # Si on reçoit list_id = -1 lors d'une mise à jour, le résoudre vers la liste au plus petit order
    if "list_id" in update_data and update_data["list_id"] == -1:
        if lowest_list := db.query(KanbanList).order_by(KanbanList.order.asc()).first():
            update_data["list_id"] = lowest_list.id

        else:
            raise ValueError("Aucune liste valide n'est disponible pour mettre à jour la carte")
    # Stocker les valeurs avant modification pour l'historique
    old_values = {}
    if "title" in update_data:
        old_values["title"] = db_card.title
    if "description" in update_data:
        old_values["description"] = db_card.description
    if "priority" in update_data:
        old_values["priority"] = db_card.priority
    if "assignee_id" in update_data:
        old_values["assignee_id"] = db_card.assignee_id

    for field, value in update_data.items():
        if field not in Card.PROTECTED_FIELDS:
            setattr(db_card, field, value)

    # Mettre à jour les libellés si fournis
    if label_ids is not None:
        labels = db.query(Label).filter(Label.id.in_(label_ids)).all()
        db_card.labels = labels

    db.commit()
    db.refresh(db_card)

    # Créer des entrées d'historique spécifiques pour les modifications
    if updated_by:
        try:
            # Priorité changée
            if "priority" in old_values and old_values["priority"] != db_card.priority:
                priority_labels = {
                    CardPriority.LOW: "faible",
                    CardPriority.MEDIUM: "moyenne",
                    CardPriority.HIGH: "élevée",
                }
                old_priority_label = priority_labels.get(old_values["priority"], str(old_values["priority"]))
                new_priority_label = priority_labels.get(db_card.priority, str(db_card.priority))
                history_entry = CardHistoryCreate(
                    card_id=db_card.id,
                    user_id=updated_by,
                    action="priority_change",
                    description=f"Priorité changée de « {old_priority_label} » à « {new_priority_label} »",
                )
                card_history_service.create_card_history_entry(db, history_entry)

            # Assigné changé
            if "assignee_id" in old_values and old_values["assignee_id"] != db_card.assignee_id:
                _assignee_changed(old_values, db, db_card, updated_by)

            if other_changes := [key for key in old_values if key not in ["priority", "assignee_id"]]:
                history_entry = CardHistoryCreate(
                    card_id=db_card.id,
                    user_id=updated_by,
                    action="update",
                    description=f"Carte « {db_card.title} » modifiée",
                )
                card_history_service.create_card_history_entry(db, history_entry)

        except Exception as e:
            # Ne pas échouer la mise à jour de la carte si l'historique échoue
            print(f"Warning: Failed to create history entries for card update: {e}")

    return db_card


def _assignee_changed(old_values, db, db_card, updated_by):
    # Récupérer les noms des utilisateurs
    old_assignee = None
    new_assignee = None
    if old_values["assignee_id"]:
        old_user = db.query(User).filter(User.id == old_values["assignee_id"]).first()
        old_assignee = old_user.display_name if old_user else f"Utilisateur {old_values['assignee_id']}"
    if db_card.assignee_id:
        new_user = db.query(User).filter(User.id == db_card.assignee_id).first()
        new_assignee = new_user.display_name if new_user else f"Utilisateur {db_card.assignee_id}"

    old_assignee_text = old_assignee or "personne"
    new_assignee_text = new_assignee or "personne"
    history_entry = CardHistoryCreate(
        card_id=db_card.id,
        user_id=updated_by,
        action="assignee_change",
        description=f"Assigné changé de « {old_assignee_text} » à « {new_assignee_text} »",
    )
    card_history_service.create_card_history_entry(db, history_entry)


def update_card_list(db: Session, card_id: int, list_update: CardListUpdate) -> Optional[Card]:
    """Mettre à jour la liste d'une carte."""
    db_card = get_card(db, card_id)
    if not db_card:
        return None

    # Gérer le cas spécial list_id = -1
    target_list_id = list_update.list_id
    if target_list_id == -1:
        if lowest_list := db.query(KanbanList).order_by(KanbanList.order.asc()).first():
            target_list_id = lowest_list.id

        else:
            return None
    db_card.list_id = target_list_id
    db.commit()
    db.refresh(db_card)

    return db_card


def archive_card(db: Session, card_id: int, archived_by: Optional[int] = None) -> Optional[Card]:
    """Archiver une carte."""
    db_card = get_card(db, card_id)
    if not db_card:
        return None

    db_card.is_archived = True
    db.commit()
    db.refresh(db_card)

    # Créer une entrée d'historique pour l'archivage
    if archived_by:
        try:
            history_entry = CardHistoryCreate(
                card_id=db_card.id,
                user_id=archived_by,
                action="archive",
                description=f"Carte « {db_card.title} » archivée",
            )
            card_history_service.create_card_history_entry(db, history_entry)
        except Exception as e:
            print(f"Warning: Failed to create history entry for card archive: {e}")

    return db_card


def unarchive_card(db: Session, card_id: int, unarchived_by: Optional[int] = None) -> Optional[Card]:
    """Désarchiver une carte."""
    db_card = get_card(db, card_id)
    if not db_card:
        return None

    db_card.is_archived = False
    db.commit()
    db.refresh(db_card)

    # Créer une entrée d'historique pour la restauration
    if unarchived_by:
        try:
            history_entry = CardHistoryCreate(
                card_id=db_card.id,
                user_id=unarchived_by,
                action="unarchive",
                description=f"Carte « {db_card.title} » restaurée",
            )
            card_history_service.create_card_history_entry(db, history_entry)
        except Exception as e:
            print(f"Warning: Failed to create history entry for card unarchive: {e}")

    return db_card


def delete_card(db: Session, card_id: int) -> bool:
    """Supprimer définitivement une carte."""
    db_card = get_card(db, card_id)
    if not db_card:
        return False

    db.delete(db_card)
    db.commit()
    return True


def move_card(
    db: Session, card_id: int, move_request: CardMoveRequest, moved_by: Optional[int] = None
) -> Optional[Card]:
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

    # Récupérer le nom de l'ancienne liste pour l'historique
    old_list = db.query(KanbanList).filter(KanbanList.id == old_list_id).first()
    old_list_name = old_list.name if old_list else f"Liste {old_list_id}"

    # Si on déplace dans la même liste, on réorganise les positions
    if old_list_id == new_list_id:
        # Réorganisation dans la même liste - utiliser la position fournie ou mettre à la fin
        target_position = getattr(move_request, "position", None)
        if target_position is None:
            # Pas de position spécifiée, mettre à la fin
            max_position = db.query(func.max(Card.position)).filter(Card.list_id == new_list_id).scalar()
            target_position = (max_position or 0) + 1

        _reorder_cards_in_same_list(db, card_id, old_position, target_position, new_list_id)
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

    # Créer une entrée d'historique pour le déplacement si les listes sont différentes
    if moved_by and old_list_id != new_list_id:
        try:
            new_list = db.query(KanbanList).filter(KanbanList.id == new_list_id).first()
            new_list_name = new_list.name if new_list else f"Liste {new_list_id}"
            history_entry = CardHistoryCreate(
                card_id=db_card.id,
                user_id=moved_by,
                action="move",
                description=f"Carte « {db_card.title} » déplacée de « {old_list_name} » à « {new_list_name} »",
            )
            card_history_service.create_card_history_entry(db, history_entry)
        except Exception as e:
            print(f"Warning: Failed to create history entry for card move: {e}")

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
