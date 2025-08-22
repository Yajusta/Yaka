"""Schémas Pydantic pour les listes Kanban."""

from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
import re


class KanbanListBase(BaseModel):
    """Schéma de base pour les listes Kanban."""

    name: str = Field(..., min_length=1, max_length=100, description="Nom de la liste")
    order: int = Field(..., ge=1, description="Ordre d'affichage de la liste")

    @validator('name')
    def validate_name(cls, v):
        """Valide que le nom n'est pas vide après suppression des espaces et contient des caractères valides."""
        if not v or not v.strip():
            raise ValueError('Le nom de la liste ne peut pas être vide')
        
        # Trim whitespace
        name = v.strip()
        
        # Check minimum length after trimming
        if len(name) < 1:
            raise ValueError('Le nom de la liste doit contenir au moins 1 caractère')
        
        # Check maximum length
        if len(name) > 100:
            raise ValueError('Le nom de la liste ne peut pas dépasser 100 caractères')
        
        # Check for invalid characters (optional - basic validation)
        if re.search(r'[<>"\']', name):
            raise ValueError('Le nom de la liste contient des caractères non autorisés')
        
        return name

    @validator('order')
    def validate_order(cls, v):
        """Valide que l'ordre est un entier positif."""
        if v < 1:
            raise ValueError('L\'ordre doit être un nombre entier positif (≥ 1)')
        if v > 9999:
            raise ValueError('L\'ordre ne peut pas dépasser 9999')
        return v


class KanbanListCreate(KanbanListBase):
    """Schéma pour la création d'une liste Kanban."""
    pass


class KanbanListUpdate(BaseModel):
    """Schéma pour la mise à jour d'une liste Kanban."""

    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Nom de la liste")
    order: Optional[int] = Field(None, ge=1, description="Ordre d'affichage de la liste")

    @validator('name')
    def validate_name(cls, v):
        """Valide que le nom n'est pas vide après suppression des espaces et contient des caractères valides."""
        if v is None:
            return v
        
        if not v or not v.strip():
            raise ValueError('Le nom de la liste ne peut pas être vide')
        
        # Trim whitespace
        name = v.strip()
        
        # Check minimum length after trimming
        if len(name) < 1:
            raise ValueError('Le nom de la liste doit contenir au moins 1 caractère')
        
        # Check maximum length
        if len(name) > 100:
            raise ValueError('Le nom de la liste ne peut pas dépasser 100 caractères')
        
        # Check for invalid characters (optional - basic validation)
        if re.search(r'[<>"\']', name):
            raise ValueError('Le nom de la liste contient des caractères non autorisés')
        
        return name

    @validator('order')
    def validate_order(cls, v):
        """Valide que l'ordre est un entier positif."""
        if v is None:
            return v
        
        if v < 1:
            raise ValueError('L\'ordre doit être un nombre entier positif (≥ 1)')
        if v > 9999:
            raise ValueError('L\'ordre ne peut pas dépasser 9999')
        return v


class KanbanListResponse(KanbanListBase):
    """Schéma de réponse pour les listes Kanban."""

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ListDeletionRequest(BaseModel):
    """Schéma pour la demande de suppression d'une liste avec déplacement des cartes."""

    target_list_id: int = Field(..., description="ID de la liste de destination pour les cartes")

    @validator('target_list_id')
    def validate_target_list_id(cls, v):
        """Valide que l'ID de la liste de destination est positif."""
        if v <= 0:
            raise ValueError('L\'ID de la liste de destination doit être un entier positif')
        return v


class ListReorderRequest(BaseModel):
    """Schéma pour la réorganisation des listes."""

    list_orders: dict[int, int] = Field(..., description="Dictionnaire des ID de listes et leurs nouveaux ordres")

    @validator('list_orders')
    def validate_list_orders(cls, v):
        """Valide que tous les ordres sont positifs et uniques."""
        if not v:
            raise ValueError('Au moins une liste doit être fournie')
        
        orders = list(v.values())
        if any(order < 1 for order in orders):
            raise ValueError('Tous les ordres doivent être positifs')
        
        if len(orders) != len(set(orders)):
            raise ValueError('Les ordres doivent être uniques')
        
        return v