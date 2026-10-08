from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.domains.aggregations.constants import AggregationConditionOperator
from app.domains.tags.schemas import TagResponse


def _clean_name(value: Optional[str]) -> str:
    if value is None:
        raise ValueError("name cannot be null")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("name cannot be empty")
    return cleaned


class AggregationConditionCreate(BaseModel):
    tag_id: UUID
    operator: AggregationConditionOperator = AggregationConditionOperator.INCLUDE


class AggregationConditionResponse(BaseModel):
    id: UUID
    tag_id: UUID
    operator: AggregationConditionOperator
    tag: TagResponse

    class Config:
        from_attributes = True


class AggregationViewCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=1000)

    _validate_name = field_validator("name")(_clean_name)


class AggregationViewUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=1000)

    _validate_name = field_validator("name")(_clean_name)


class AggregationNodeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    parent_id: Optional[UUID] = None
    display_order: int = Field(default=0, ge=0)
    conditions: List[AggregationConditionCreate] = Field(default_factory=list)

    _validate_name = field_validator("name")(_clean_name)

    @field_validator("conditions")
    @classmethod
    def validate_unique_condition_tags(cls, value):
        tag_ids = [condition.tag_id for condition in value]
        if len(set(tag_ids)) != len(tag_ids):
            raise ValueError("conditions must not repeat a tag")
        return value


class AggregationNodeUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    parent_id: Optional[UUID] = None
    display_order: Optional[int] = Field(default=None, ge=0)
    conditions: Optional[List[AggregationConditionCreate]] = None

    _validate_name = field_validator("name")(_clean_name)

    @field_validator("conditions")
    @classmethod
    def validate_unique_condition_tags(cls, value):
        if value is None:
            return value
        tag_ids = [condition.tag_id for condition in value]
        if len(set(tag_ids)) != len(tag_ids):
            raise ValueError("conditions must not repeat a tag")
        return value


class AggregationNodeResponse(BaseModel):
    id: UUID
    view_id: UUID
    parent_id: Optional[UUID]
    name: str
    display_order: int
    conditions: List[AggregationConditionResponse] = Field(default_factory=list)
    children: List["AggregationNodeResponse"] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AggregationViewSummaryResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AggregationViewResponse(AggregationViewSummaryResponse):
    nodes: List[AggregationNodeResponse] = Field(default_factory=list)


class AggregationNodeResult(BaseModel):
    node_id: UUID
    name: str
    total: Decimal
    transaction_count: int
    children: List["AggregationNodeResult"] = Field(default_factory=list)


class AggregationViewResult(BaseModel):
    view_id: UUID
    name: str
    nodes: List[AggregationNodeResult]
