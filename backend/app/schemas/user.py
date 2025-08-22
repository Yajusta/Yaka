"""Schémas Pydantic pour les utilisateurs."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from ..models.user import UserRole


class UserBase(BaseModel):
    """Schéma de base pour les utilisateurs."""

    email: str
    display_name: Optional[str] = Field(None, max_length=32, description="Nom affiché (32 caractères max)")
    role: UserRole = UserRole.USER


class UserCreate(UserBase):
    """Schéma pour la création d'un utilisateur."""

    password: str


class UserUpdate(BaseModel):
    """Schéma pour la mise à jour d'un utilisateur."""

    email: Optional[str] = None
    display_name: Optional[str] = Field(None, max_length=32, description="Nom affiché (32 caractères max)")
    role: Optional[UserRole] = None
    password: Optional[str] = None


class SetPasswordPayload(BaseModel):
    """Schéma pour définir un mot de passe via un token d'invitation."""

    token: str
    password: str


class PasswordResetRequest(BaseModel):
    """Schéma pour demander une réinitialisation de mot de passe."""

    email: str


class UserResponse(UserBase):
    """Schéma de réponse pour les utilisateurs."""

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserListItem(BaseModel):
    """Schéma minimal pour la liste d'utilisateurs (utilisé par les non-admins)."""

    id: int
    display_name: Optional[str] = Field(None, max_length=32, description="Nom affiché (32 caractères max)")
    role: Optional[UserRole] = UserRole.USER
    status: Optional[str] = None
    # email est optionnel ici : les non-admins recevront une liste sans email
    email: Optional[str] = None

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """Schéma pour la connexion utilisateur."""

    email: str
    password: str
