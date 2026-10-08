from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.domains.tags.constants import MAX_TAGS_PER_ENTITY


def _clean_name(value: Optional[str]) -> str:
    if value is None:
        raise ValueError("name cannot be null")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("name cannot be empty")
    return cleaned


def _unique_tag_ids(value: Optional[List[UUID]]) -> List[UUID]:
    if value is None:
        raise ValueError("tag_ids cannot be null")
    if len(set(value)) != len(value):
        raise ValueError("tag_ids must not contain duplicates")
    return value


class TagGroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    tag_ids: List[UUID] = Field(min_length=1, max_length=MAX_TAGS_PER_ENTITY)
    parent_id: Optional[UUID] = None
    display_order: int = Field(default=0, ge=0)

    _validate_name = field_validator("name")(_clean_name)
    _validate_tag_ids = field_validator("tag_ids")(_unique_tag_ids)


class TagGroupUpdate(BaseModel):
    """Partial update. `parent_id: null` moves the group to the top level;
    `name` and `tag_ids` cannot be null."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    tag_ids: Optional[List[UUID]] = Field(
        default=None, min_length=1, max_length=MAX_TAGS_PER_ENTITY
    )
    parent_id: Optional[UUID] = None
    display_order: Optional[int] = Field(default=None, ge=0)

    _validate_name = field_validator("name")(_clean_name)
    _validate_tag_ids = field_validator("tag_ids")(_unique_tag_ids)


class TagGroupResponse(BaseModel):
    id: UUID
    name: str
    parent_id: Optional[UUID]
    tag_ids: List[UUID]
    effective_tag_ids: List[UUID]
    display_order: int
    created_at: datetime
    updated_at: datetime


class TagGroupSummaryItem(BaseModel):
    group_id: UUID
    total: Decimal
    count: int


class TagGroupOverlapItem(BaseModel):
    transaction_id: UUID
    description: str
    amount: Decimal
    date: datetime
    group_ids: List[UUID]
