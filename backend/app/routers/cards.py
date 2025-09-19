"""Routeur pour la gestion des cartes."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas import (
    CardCreate,
    CardUpdate,
    CardListUpdate,
    CardResponse,
    CardFilter,
    CardMoveRequest,
    BulkCardMoveRequest,
)
from ..services import card as card_service
from ..utils.dependencies import get_current_active_user
from ..models import User, CardPriority
from ..schemas import CardHistoryCreate, CardHistoryResponse
from ..services import card_history as card_history_service

router = APIRouter(prefix="/cards", tags=["cartes"])


@router.get("/", response_model=List[CardResponse])
async def read_cards(
    skip: int = 0,
    limit: int = 100,
    list_id: int = Query(None, description="Filtrer par liste Kanban"),
    statut: str = Query(None, description="Filtrer par statut (compatibilité)"),
    assignee_id: int = Query(None, description="Filtrer par utilisateur assigné"),
    priority: CardPriority = Query(None, description="Filtrer par priorité"),
    label_id: int = Query(None, description="Filtrer par libellé"),
    search: str = Query(None, description="Recherche textuelle"),
    include_archived: bool = Query(False, description="Inclure les cartes archivées"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Récupérer la liste des cartes avec filtres optionnels."""
    # Gérer la compatibilité avec l'ancien paramètre statut
    effective_list_id = list_id
    if statut and not list_id:
        statut_to_list_id = {"a_faire": 1, "en_cours": 2, "termine": 3}
        effective_list_id = statut_to_list_id.get(statut)
        if effective_list_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Statut invalide: {statut}. Valeurs acceptées: a_faire, en_cours, termine",
            )

    filters = CardFilter(
        list_id=effective_list_id,
        assignee_id=assignee_id,
        priority=priority,
        label_id=label_id,
        search=search,
        include_archived=include_archived,
    )
    return card_service.get_cards(db, filters=filters, skip=skip, limit=limit)


@router.get("/archived", response_model=List[CardResponse])
async def read_archived_cards(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Récupérer la liste des cartes archivées."""
    return card_service.get_archived_cards(db, skip=skip, limit=limit)


@router.post("/", response_model=CardResponse)
async def create_card(
    card: CardCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """Créer une nouvelle carte."""
    try:
        return card_service.create_card(db=db, card=card, created_by=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/{card_id}", response_model=CardResponse)
async def read_card(
    card_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """Récupérer une carte par son ID."""
    db_card = card_service.get_card(db, card_id=card_id)
    if db_card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carte non trouvée")
    return db_card


@router.put("/{card_id}", response_model=CardResponse)
async def update_card(
    card_id: int,
    card_update: CardUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Mettre à jour une carte."""
    db_card = card_service.update_card(db, card_id=card_id, card_update=card_update, updated_by=current_user.id)
    if db_card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carte non trouvée")
    return db_card


@router.patch("/{card_id}/list", response_model=CardResponse)
async def update_card_list(
    card_id: int,
    list_update: CardListUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Mettre à jour la liste d'une carte (pour le drag & drop)."""
    db_card = card_service.update_card_list(db, card_id=card_id, list_update=list_update)
    if db_card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carte non trouvée")
    return db_card


@router.patch("/{card_id}/archive", response_model=CardResponse)
async def archive_card(
    card_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """Archiver une carte."""
    db_card = card_service.archive_card(db, card_id=card_id, archived_by=current_user.id)
    if db_card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carte non trouvée")
    return db_card


@router.patch("/{card_id}/unarchive", response_model=CardResponse)
async def unarchive_card(
    card_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """Désarchiver une carte."""
    db_card = card_service.unarchive_card(db, card_id=card_id, unarchived_by=current_user.id)
    if db_card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carte non trouvée")
    return db_card


@router.patch("/{card_id}/move", response_model=CardResponse)
async def move_card(
    card_id: int,
    move_request: CardMoveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Déplacer une carte entre listes avec gestion de position."""
    db_card = card_service.move_card(db, card_id=card_id, move_request=move_request, moved_by=current_user.id)
    if db_card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carte non trouvée")
    return db_card


@router.post("/bulk-move", response_model=List[CardResponse])
async def bulk_move_cards(
    bulk_move_request: BulkCardMoveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Déplacer plusieurs cartes vers une liste de destination."""
    if moved_cards := card_service.bulk_move_cards(db, bulk_move_request=bulk_move_request):
        return moved_cards
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucune carte trouvée ou déplacée")


# Backward compatibility endpoints for statut-based operations
@router.patch("/{card_id}/statut", response_model=CardResponse)
async def update_card_statut_legacy(
    card_id: int, statut: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """Mettre à jour le statut d'une carte (endpoint de compatibilité)."""
    # Mapper les anciens statuts vers les list_id
    statut_to_list_id = {"a_faire": 1, "en_cours": 2, "termine": 3}

    if statut not in statut_to_list_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Statut invalide: {statut}. Valeurs acceptées: a_faire, en_cours, termine",
        )

    list_update = CardListUpdate(list_id=statut_to_list_id[statut])
    db_card = card_service.update_card_list(db, card_id=card_id, list_update=list_update)
    if db_card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carte non trouvée")
    return db_card


@router.delete("/{card_id}")
async def delete_card(
    card_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """Supprimer définitivement une carte."""
    if success := card_service.delete_card(db, card_id=card_id):
        return {"message": "Carte supprimée avec succès"}
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carte non trouvée")


@router.get("/{card_id}/history", response_model=List[CardHistoryResponse])
async def get_card_history(
    card_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """Récupérer l'historique complet d'une carte."""
    # Vérifier que la carte existe
    db_card = card_service.get_card(db, card_id=card_id)
    if db_card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carte non trouvée")

    return card_history_service.get_card_history(db, card_id=card_id)


@router.post("/{card_id}/history", response_model=CardHistoryResponse)
async def create_card_history_entry(
    card_id: int,
    history_entry: CardHistoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Ajouter une entrée à l'historique d'une carte."""
    # Vérifier que la carte existe
    db_card = card_service.get_card(db, card_id=card_id)
    if db_card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carte non trouvée")

    return card_history_service.create_card_history_entry(db, history_entry)
