from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


def _clean_name(value: Optional[str]) -> str:
    if value is None:
        raise ValueError("name cannot be null")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("name cannot be empty")
    return cleaned


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    display_order: int = Field(default=0, ge=0)

    _validate_name = field_validator("name")(_clean_name)


class TagUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    display_order: Optional[int] = Field(default=None, ge=0)

    _validate_name = field_validator("name")(_clean_name)


class TagResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    display_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TagUsageResponse(TagResponse):
    """Tag as returned by the list endpoint, with how many records use it."""

    usage_count: int


class TagListResponse(BaseModel):
    data: List[TagResponse]
