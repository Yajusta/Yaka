"""Service pour la gestion des listes Kanban."""

from typing import Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import Card, KanbanList
from ..schemas import KanbanListCreate, KanbanListUpdate


class KanbanListService:
    """Service pour la gestion des listes Kanban."""

    @staticmethod
    def get_lists(db: Session) -> List[KanbanList]:
        """Récupérer toutes les listes ordonnées par ordre d'affichage."""
        return db.query(KanbanList).order_by(KanbanList.order).all()

    @staticmethod
    def get_list(db: Session, list_id: int) -> Optional[KanbanList]:
        """Récupérer une liste par son ID."""
        return db.query(KanbanList).filter(KanbanList.id == list_id).first()

    @staticmethod
    def get_list_with_cards_count(db: Session, list_id: int) -> Tuple[Optional[KanbanList], int]:
        """
        Récupérer une liste avec le nombre de cartes actives qu'elle contient.
        Ne compte que les cartes non archivées (is_archived = False).

        Args:
            db: Session de base de données
            list_id: ID de la liste

        Returns:
            Tuple[Optional[KanbanList], int]: La liste et le nombre de cartes actives
        """
        # Validation de l'ID
        if list_id <= 0:
            raise ValueError("L'ID de la liste doit être un entier positif")

        kanban_list = db.query(KanbanList).filter(KanbanList.id == list_id).first()
        if not kanban_list:
            return None, 0

        try:
            # Ne compter que les cartes actives (non archivées)
            cards_count = db.query(Card).filter(Card.list_id == list_id, Card.is_archived == False).count()
            return kanban_list, cards_count
        except Exception as e:
            raise ValueError(f"Erreur lors du comptage des cartes: {str(e)}") from e

    @staticmethod
    def create_list(db: Session, list_data: KanbanListCreate) -> KanbanList:
        """
        Créer une nouvelle liste avec validation complète.

        Args:
            db: Session de base de données
            list_data: Données de la liste à créer

        Returns:
            KanbanList: La liste créée

        Raises:
            ValueError: Si la validation échoue
        """
        if (
            existing_list := db.query(KanbanList)
            .filter(func.lower(KanbanList.name) == func.lower(list_data.name))
            .first()
        ):
            raise ValueError(f"Une liste avec le nom '{list_data.name}' existe déjà (la casse est ignorée)")

        # Validation de l'ordre - vérifier les limites
        if list_data.order < 1:
            raise ValueError("L'ordre doit être un nombre entier positif (≥ 1)")

        if list_data.order > 9999:
            raise ValueError("L'ordre ne peut pas dépasser 9999")

        # Vérifier le nombre maximum de listes (limite raisonnable)
        total_lists = db.query(KanbanList).count()
        if total_lists >= 50:
            raise ValueError(
                "Nombre maximum de listes atteint (50). Supprimez des listes existantes avant d'en créer de nouvelles."
            )

        if existing_order := db.query(KanbanList).filter(KanbanList.order == list_data.order).first():
            # Décaler tous les ordres supérieurs ou égaux
            KanbanListService._shift_orders_up(db, list_data.order)

        try:
            db_list = KanbanList(name=list_data.name, description=list_data.description, order=list_data.order)

            db.add(db_list)
            db.commit()
            db.refresh(db_list)
            return db_list
        except Exception as e:
            db.rollback()
            raise ValueError(f"Erreur lors de la création de la liste: {str(e)}") from e

    @staticmethod
    def update_list(db: Session, list_id: int, list_data: KanbanListUpdate) -> Optional[KanbanList]:
        """
        Mettre à jour une liste avec validation complète.

        Args:
            db: Session de base de données
            list_id: ID de la liste à mettre à jour
            list_data: Nouvelles données de la liste

        Returns:
            Optional[KanbanList]: La liste mise à jour ou None si non trouvée

        Raises:
            ValueError: Si la validation échoue
        """
        db_list = KanbanListService.get_list(db, list_id)
        if not db_list:
            return None

        update_data = list_data.model_dump(exclude_unset=True)

        # Si aucune donnée à mettre à jour
        if not update_data:
            raise ValueError("Aucune donnée fournie pour la mise à jour")

        # Vérifier l'unicité du nom si fourni (case-insensitive)
        if "name" in update_data:
            if existing_list := (
                db.query(KanbanList)
                .filter(
                    func.lower(KanbanList.name) == func.lower(update_data["name"]),
                    KanbanList.id != list_id,
                )
                .first()
            ):
                raise ValueError(f"Une liste avec le nom '{update_data['name']}' existe déjà (la casse est ignorée)")

        # Gérer le changement d'ordre si fourni
        if "order" in update_data:
            new_order = update_data["order"]
            old_order = db_list.order

            # Validation de l'ordre
            if new_order < 1:
                raise ValueError("L'ordre doit être un nombre entier positif (≥ 1)")

            if new_order > 9999:
                raise ValueError("L'ordre ne peut pas dépasser 9999")

            if new_order != old_order:
                if existing_order := (
                    db.query(KanbanList).filter(KanbanList.order == new_order, KanbanList.id != list_id).first()
                ):
                    # Réorganiser les ordres
                    KanbanListService._reorder_lists_for_update(db, list_id, old_order, new_order)

        try:
            # Appliquer les modifications
            for field, value in update_data.items():
                setattr(db_list, field, value)

            db.commit()
            db.refresh(db_list)
            return db_list
        except Exception as e:
            db.rollback()
            raise ValueError(f"Erreur lors de la mise à jour de la liste: {str(e)}") from e

    @staticmethod
    def delete_list(db: Session, list_id: int, target_list_id: int) -> bool:
        """
        Supprimer une liste après avoir déplacé toutes ses cartes vers une autre liste.

        Args:
            db: Session de base de données
            list_id: ID de la liste à supprimer
            target_list_id: ID de la liste de destination pour les cartes

        Returns:
            bool: True si la suppression a réussi, False sinon

        Raises:
            ValueError: Si la validation échoue
        """
        # Validation des IDs
        if list_id <= 0:
            raise ValueError("L'ID de la liste à supprimer doit être un entier positif")

        if target_list_id <= 0:
            raise ValueError("L'ID de la liste de destination doit être un entier positif")

        # Vérifier qu'il restera au moins une liste après suppression (Requirement 4.1)
        total_lists = db.query(KanbanList).count()
        if total_lists <= 1:
            raise ValueError(
                "Impossible de supprimer la dernière liste. Au moins une liste doit exister dans le système."
            )

        # Vérifier que la liste à supprimer existe
        list_to_delete = KanbanListService.get_list(db, list_id)
        if not list_to_delete:
            raise ValueError(f"La liste avec l'ID {list_id} n'existe pas")

        # Vérifier que la liste de destination existe et est différente (Requirement 4.2)
        target_list = KanbanListService.get_list(db, target_list_id)
        if not target_list:
            raise ValueError(f"La liste de destination avec l'ID {target_list_id} n'existe pas")

        if list_id == target_list_id:
            raise ValueError("La liste de destination ne peut pas être la même que la liste à supprimer")

        try:
            # Compter les cartes à déplacer pour information
            cards_count = db.query(Card).filter(Card.list_id == list_id).count()

            # Déplacer toutes les cartes vers la liste de destination (Requirement 4.4)
            if cards_count > 0:
                cards_moved = db.query(Card).filter(Card.list_id == list_id).update({Card.list_id: target_list_id})

                if cards_moved != cards_count:
                    raise ValueError(
                        f"Erreur lors du déplacement des cartes: {cards_moved} cartes déplacées sur {cards_count} attendues"
                    )

            # Supprimer la liste
            db.delete(list_to_delete)

            # Réorganiser les ordres pour combler le trou
            KanbanListService._compact_orders(db, list_to_delete.order)

            db.commit()
            return True

        except Exception as e:
            db.rollback()
            if isinstance(e, ValueError):
                raise e
            else:
                raise ValueError(f"Erreur lors de la suppression de la liste: {str(e)}") from e

    @staticmethod
    def reorder_lists(db: Session, list_orders: Dict[int, int]) -> bool:
        """
        Réorganiser l'ordre de plusieurs listes.

        Args:
            db: Session de base de données
            list_orders: Dictionnaire {list_id: new_order}

        Returns:
            bool: True si la réorganisation a réussi

        Raises:
            ValueError: Si la validation échoue
        """
        # Vérifier que toutes les listes existent
        list_ids = list(list_orders.keys())
        existing_lists = db.query(KanbanList).filter(KanbanList.id.in_(list_ids)).all()

        if len(existing_lists) != len(list_ids):
            existing_ids = {lst.id for lst in existing_lists}
            missing_ids = set(list_ids) - existing_ids
            raise ValueError(f"Les listes suivantes n'existent pas: {missing_ids}")

        # Vérifier que tous les ordres sont positifs et uniques
        orders = list(list_orders.values())
        if any(order < 1 for order in orders):
            raise ValueError("Tous les ordres doivent être positifs")

        if len(orders) != len(set(orders)):
            raise ValueError("Les ordres doivent être uniques")

        # Appliquer les nouveaux ordres
        for list_id, new_order in list_orders.items():
            db.query(KanbanList).filter(KanbanList.id == list_id).update({KanbanList.order: new_order})

        db.commit()
        return True

    @staticmethod
    def _shift_orders_up(db: Session, from_order: int) -> None:
        """Décaler tous les ordres supérieurs ou égaux vers le haut."""
        db.query(KanbanList).filter(KanbanList.order >= from_order).update(
            {KanbanList.order: KanbanList.order + 1}, synchronize_session="evaluate"
        )

    @staticmethod
    def _compact_orders(db: Session, deleted_order: int) -> None:
        """Compacter les ordres après suppression d'une liste."""
        db.query(KanbanList).filter(KanbanList.order > deleted_order).update(
            {KanbanList.order: KanbanList.order - 1}, synchronize_session="evaluate"
        )

    @staticmethod
    def _reorder_lists_for_update(db: Session, list_id: int, old_order: int, new_order: int) -> None:
        """Réorganiser les ordres lors de la mise à jour d'une liste."""
        if new_order > old_order:
            # Déplacer vers le bas : décaler les listes entre old_order+1 et new_order vers le haut
            db.query(KanbanList).filter(
                KanbanList.order > old_order, KanbanList.order <= new_order, KanbanList.id != list_id
            ).update({KanbanList.order: KanbanList.order - 1})
        else:
            # Déplacer vers le haut : décaler les listes entre new_order et old_order-1 vers le bas
            db.query(KanbanList).filter(
                KanbanList.order >= new_order, KanbanList.order < old_order, KanbanList.id != list_id
            ).update({KanbanList.order: KanbanList.order + 1})


# Fonctions utilitaires pour maintenir la compatibilité avec le pattern existant
def get_lists(db: Session) -> List[KanbanList]:
    """Récupérer toutes les listes ordonnées par ordre d'affichage."""
    return KanbanListService.get_lists(db)


def get_list(db: Session, list_id: int) -> Optional[KanbanList]:
    """Récupérer une liste par son ID."""
    return KanbanListService.get_list(db, list_id)


def get_list_with_cards_count(db: Session, list_id: int) -> Tuple[Optional[KanbanList], int]:
    """Récupérer une liste avec le nombre de cartes qu'elle contient."""
    return KanbanListService.get_list_with_cards_count(db, list_id)


def create_list(db: Session, list_data: KanbanListCreate) -> KanbanList:
    """Créer une nouvelle liste."""
    return KanbanListService.create_list(db, list_data)


def update_list(db: Session, list_id: int, list_data: KanbanListUpdate) -> Optional[KanbanList]:
    """Mettre à jour une liste."""
    return KanbanListService.update_list(db, list_id, list_data)


def delete_list(db: Session, list_id: int, target_list_id: int) -> bool:
    """Supprimer une liste après avoir déplacé toutes ses cartes vers une autre liste."""
    return KanbanListService.delete_list(db, list_id, target_list_id)


def reorder_lists(db: Session, list_orders: Dict[int, int]) -> bool:
    """Réorganiser l'ordre de plusieurs listes."""
    return KanbanListService.reorder_lists(db, list_orders)
