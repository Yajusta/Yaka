"""Pydantic schemas for personal dictionary entries."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .global_dictionary import DictionaryEntryBase


class PersonalDictionaryBase(DictionaryEntryBase):
    """Base schema for personal dictionary entries.
    
    Inherits term and definition validation from DictionaryEntryBase.
    """

    pass


class PersonalDictionaryCreate(PersonalDictionaryBase):
    """Schema for creating a personal dictionary entry."""

    pass


class PersonalDictionaryUpdate(BaseModel):
    """Schema for updating a personal dictionary entry."""

    term: Optional[str] = Field(default=None, max_length=32, description="Term or expression (32 characters max)")
    definition: Optional[str] = Field(default=None, max_length=250, description="Definition (250 characters max)")


class PersonalDictionaryResponse(PersonalDictionaryBase):
    """Schema for personal dictionary entry response."""

    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)

