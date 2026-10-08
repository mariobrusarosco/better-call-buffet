from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.domains.tags.constants import TagSelectionMode


def _clean_name(value: Optional[str]) -> str:
    if value is None:
        raise ValueError("name cannot be null")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("name cannot be empty")
    return cleaned


class TagDimensionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    selection_mode: TagSelectionMode = TagSelectionMode.MULTIPLE
    display_order: int = Field(default=0, ge=0)

    _validate_name = field_validator("name")(_clean_name)


class TagDimensionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    selection_mode: Optional[TagSelectionMode] = None
    display_order: Optional[int] = Field(default=None, ge=0)

    _validate_name = field_validator("name")(_clean_name)


class TagDimensionResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    selection_mode: TagSelectionMode
    display_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    dimension_id: Optional[UUID] = None
    display_order: int = Field(default=0, ge=0)

    _validate_name = field_validator("name")(_clean_name)


class TagUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    dimension_id: Optional[UUID] = None
    display_order: Optional[int] = Field(default=None, ge=0)

    _validate_name = field_validator("name")(_clean_name)


class TagResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    dimension_id: Optional[UUID]
    display_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    dimension: Optional[TagDimensionResponse] = None

    class Config:
        from_attributes = True


class TagListResponse(BaseModel):
    data: List[TagResponse]
