"""Service pour la gestion des libellés."""

from sqlalchemy.orm import Session
from typing import Optional, List
from ..models import Label
from ..schemas import LabelCreate, LabelUpdate


def get_label(db: Session, label_id: int) -> Optional[Label]:
    """Récupérer un libellé par son ID."""
    return db.query(Label).filter(Label.id == label_id).first()


def get_labels(db: Session, skip: int = 0, limit: int = 100) -> List[Label]:
    """Récupérer une liste de libellés."""
    return db.query(Label).offset(skip).limit(limit).all()


def get_label_by_name(db: Session, nom: str) -> Optional[Label]:
    """Récupérer un libellé par son nom."""
    return db.query(Label).filter(Label.nom == nom).first()


def create_label(db: Session, label: LabelCreate, created_by: int) -> Label:
    """Créer un nouveau libellé."""
    db_label = Label(
        nom=label.nom,
        couleur=label.couleur,
        created_by=created_by
    )
    db.add(db_label)
    db.commit()
    db.refresh(db_label)
    return db_label


def update_label(db: Session, label_id: int, label_update: LabelUpdate) -> Optional[Label]:
    """Mettre à jour un libellé."""
    db_label = get_label(db, label_id)
    if not db_label:
        return None
    
    update_data = label_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_label, field, value)
    
    db.commit()
    db.refresh(db_label)
    return db_label


def delete_label(db: Session, label_id: int) -> bool:
    """Supprimer un libellé."""
    db_label = get_label(db, label_id)
    if not db_label:
        return False
    
    db.delete(db_label)
    db.commit()
    return True

