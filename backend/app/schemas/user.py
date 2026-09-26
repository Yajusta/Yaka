"""Schémas Pydantic pour les utilisateurs."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..models.user import UserRole, UserStatus, ViewScope


def _validate_email(value: str | None) -> str | None:
    """Valide une adresse email basique sans dépendance externe."""
    if value is None:
        return None
    value = value.strip()
    if "@" not in value or value.count("@") != 1:
        raise ValueError("Adresse email invalide")
    local_part, domain = value.split("@", 1)
    if not local_part or not domain or "." not in domain:
        raise ValueError("Adresse email invalide")
    return value.lower()


BCRYPT_MAX_PASSWORD_BYTES = 72


def _validate_password_strength(value: str) -> str:
    """Valide la complexité du mot de passe."""
    if len(value) < 8:
        raise ValueError("Le mot de passe doit contenir au moins 8 caractères")
    # bcrypt (>= 5) refuse au-delà de 72 octets : rejeter en 422 plutôt
    # qu'échouer au hachage
    if len(value.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError(
            f"Le mot de passe ne doit pas dépasser {BCRYPT_MAX_PASSWORD_BYTES} octets"
        )

    # Vérifier la présence de différents types de caractères
    has_upper = any(c.isupper() for c in value)
    has_lower = any(c.islower() for c in value)
    has_digit = any(c.isdigit() for c in value)

    if not (has_upper and has_lower and has_digit):
        raise ValueError(
            "Le mot de passe doit contenir au moins une majuscule, une minuscule et un chiffre"
        )

    return value


class UserBase(BaseModel):
    """Schéma de base pour les utilisateurs."""

    email: str

    @field_validator("email")
    @classmethod
    def _ensure_valid_email(cls, value: str) -> str:
        validated = _validate_email(value)
        if validated is None:
            raise ValueError("Adresse email invalide")
        return validated

    display_name: Optional[str] = Field(
        None, max_length=32, description="Nom affiché (32 caractères max)"
    )
    role: UserRole = UserRole.VISITOR
    language: Optional[str] = Field("fr", description="Langue préférée (fr, en, etc.)")
    view_scope: ViewScope = ViewScope.ALL


class UserCreate(UserBase):
    """Schéma pour la création d'un utilisateur."""

    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        """Valide la complexité du mot de passe."""
        return _validate_password_strength(value)


class UserUpdate(BaseModel):
    """Schéma pour la mise à jour d'un utilisateur."""

    email: Optional[str] = None

    @field_validator("email")
    @classmethod
    def _ensure_valid_optional_email(cls, value: str | None) -> str | None:
        return _validate_email(value)

    display_name: Optional[str] = Field(
        None, max_length=32, description="Nom affiché (32 caractères max)"
    )
    role: Optional[UserRole] = None
    language: Optional[str] = Field(None, description="Langue préférée (fr, en, etc.)")
    view_scope: Optional[ViewScope] = None
    password: Optional[str] = Field(None, min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_optional_password_strength(cls, value: Optional[str]) -> Optional[str]:
        """Valide la complexité du mot de passe si fourni."""
        return None if value is None else _validate_password_strength(value)


class LanguageUpdate(BaseModel):
    """Schéma pour la mise à jour de la langue uniquement."""

    language: str = Field(..., description="Langue préférée (fr, en, etc.)")


class ViewScopeUpdate(BaseModel):
    """Schema for updating view scope only."""

    view_scope: ViewScope = Field(
        ..., description="View scope for card access permissions"
    )


class SetPasswordPayload(BaseModel):
    """Schéma pour définir un mot de passe via un token d'invitation."""

    token: str = Field(..., min_length=32, max_length=512)
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        """Valide la complexité du mot de passe."""
        return _validate_password_strength(value)


class PasswordChange(BaseModel):
    """Schéma pour changer son propre mot de passe (utilisateur connecté)."""

    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        """Valide la complexité du mot de passe."""
        return _validate_password_strength(value)


class PasswordResetRequest(BaseModel):
    """Schéma pour demander une réinitialisation de mot de passe."""

    email: str
    board_uid: Optional[str] = None

    @field_validator("email")
    @classmethod
    def _ensure_valid_email(cls, value: str) -> str:
        validated = _validate_email(value)
        if validated is None:
            raise ValueError("Adresse email invalide")
        return validated


class UserResponse(UserBase):
    """Schéma de réponse pour les utilisateurs."""

    id: int
    must_change_password: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserListItem(BaseModel):
    """Schéma minimal pour la liste d'utilisateurs (utilisé par les non-admins)."""

    id: int
    display_name: Optional[str] = Field(
        None, max_length=32, description="Nom affiché (32 caractères max)"
    )
    role: Optional[UserRole] = UserRole.VISITOR
    status: Optional[UserStatus] = None
    view_scope: Optional[ViewScope] = ViewScope.ALL
    invited_at: Optional[datetime] = None
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
        if validated is None:
            raise ValueError("Adresse email invalide")
        return validated

    password: str = Field(..., min_length=1, max_length=32)
