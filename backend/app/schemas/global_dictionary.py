"""Pydantic schemas for global dictionary entries."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DictionaryEntryBase(BaseModel):
    """Base schema for dictionary entries with common validation logic."""

    term: str = Field(..., min_length=1, max_length=32, description="Term or expression (32 characters max)")
    definition: str = Field(..., min_length=1, max_length=250, description="Definition (250 characters max)")

    @field_validator("term")
    @classmethod
    def validate_term(cls, value: str) -> str:
        """Validate that the term does not contain dangerous patterns."""
        value = value.strip()
        if not value:
            raise ValueError("Term cannot be empty")

        # Prevent XSS injections by checking for HTML tags
        dangerous_patterns = ["<script", "</script", "<img", "javascript:", "onerror=", "onclick=", "<iframe"]
        value_lower = value.lower()
        for pattern in dangerous_patterns:
            if pattern in value_lower:
                raise ValueError("Term contains unauthorized patterns")

        return value

    @field_validator("definition")
    @classmethod
    def validate_definition(cls, value: str) -> str:
        """Validate that the definition does not contain dangerous patterns."""
        value = value.strip()
        if not value:
            raise ValueError("Definition cannot be empty")

        # Prevent XSS injections by checking for HTML tags
        dangerous_patterns = ["<script", "</script", "<img", "javascript:", "onerror=", "onclick=", "<iframe"]
        value_lower = value.lower()
        for pattern in dangerous_patterns:
            if pattern in value_lower:
                raise ValueError("Definition contains unauthorized patterns")

        return value


class GlobalDictionaryBase(DictionaryEntryBase):
    """Base schema for global dictionary entries."""

    pass


class GlobalDictionaryCreate(GlobalDictionaryBase):
    """Schema for creating a global dictionary entry."""

    pass


class GlobalDictionaryUpdate(BaseModel):
    """Schema for updating a global dictionary entry."""

    term: Optional[str] = Field(default=None, max_length=32, description="Term or expression (32 characters max)")
    definition: Optional[str] = Field(default=None, max_length=250, description="Definition (250 characters max)")


class GlobalDictionaryResponse(GlobalDictionaryBase):
    """Schema for global dictionary entry response."""

    id: int

    model_config = ConfigDict(from_attributes=True)

