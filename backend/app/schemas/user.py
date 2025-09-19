"""Schémas Pydantic pour les utilisateurs."""

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional
from datetime import datetime
from ..models.user import UserRole



def _validate_email(value: str | None) -> str | None:
    """Valide une adresse email basique sans dépendance externe."""
    if value is None:
        return None
    if "@" not in value or value.count("@") != 1:
        raise ValueError("Adresse email invalide")
    local_part, domain = value.split("@", 1)
    if not local_part or not domain or "." not in domain:
        raise ValueError("Adresse email invalide")
    return value


class UserBase(BaseModel):
    """Schéma de base pour les utilisateurs."""

    email: str

    @field_validator("email")
    @classmethod
    def _ensure_valid_email(cls, value: str) -> str:
        validated = _validate_email(value)
        assert validated is not None
        return validated

    display_name: Optional[str] = Field(None, max_length=32, description="Nom affiché (32 caractères max)")
    role: UserRole = UserRole.USER
    language: Optional[str] = Field('fr', description="Langue préférée (fr, en, etc.)")


class UserCreate(UserBase):
    """Schéma pour la création d'un utilisateur."""

    password: str


class UserUpdate(BaseModel):
    """Schéma pour la mise à jour d'un utilisateur."""

    email: Optional[str] = None

    @field_validator("email")
    @classmethod
    def _ensure_valid_optional_email(cls, value: str | None) -> str | None:
        return _validate_email(value)

    display_name: Optional[str] = Field(None, max_length=32, description="Nom affiché (32 caractères max)")
    role: Optional[UserRole] = None
    language: Optional[str] = Field(None, description="Langue préférée (fr, en, etc.)")
    password: Optional[str] = None


class LanguageUpdate(BaseModel):
    """Schéma pour la mise à jour de la langue uniquement."""

    language: str = Field(..., description="Langue préférée (fr, en, etc.)")


class SetPasswordPayload(BaseModel):
    """Schéma pour définir un mot de passe via un token d'invitation."""

    token: str
    password: str


class PasswordResetRequest(BaseModel):
    """Schéma pour demander une réinitialisation de mot de passe."""

    email: str

    @field_validator("email")
    @classmethod
    def _ensure_valid_email(cls, value: str) -> str:
        validated = _validate_email(value)
        assert validated is not None
        return validated



class UserResponse(UserBase):
    """Schéma de réponse pour les utilisateurs."""

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserListItem(BaseModel):
    """Schéma minimal pour la liste d'utilisateurs (utilisé par les non-admins)."""

    id: int
    display_name: Optional[str] = Field(None, max_length=32, description="Nom affiché (32 caractères max)")
    role: Optional[UserRole] = UserRole.USER
    status: Optional[str] = None
    # email est optionnel ici : les non-admins recevront une liste sans email
    email: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    """Schéma pour la connexion utilisateur."""

    email: str

    @field_validator("email")
    @classmethod
    def _ensure_valid_email(cls, value: str) -> str:
        validated = _validate_email(value)
        assert validated is not None
        return validated

    password: str

