from datetime import date, datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domains.tags.constants import MAX_TAGS_PER_ENTITY
from app.domains.tags.schemas import TagResponse
from app.domains.vendors.schemas import VendorResponse


class InstallmentPlanStatus(str, Enum):
    active = "active"
    finished = "finished"
    cancelled = "cancelled"


class InstallmentStatus(str, Enum):
    pending = "pending"
    linked = "linked"


class InstallmentBase(BaseModel):
    number: int
    amount: float
    due_date: date
    status: InstallmentStatus = InstallmentStatus.pending


class InstallmentUpdate(BaseModel):
    """Payload for updating an individual installment's projected data."""

    amount: Optional[float] = None
    due_date: Optional[date] = None
    status: Optional[InstallmentStatus] = None


class InstallmentResponse(InstallmentBase):
    id: UUID
    plan_id: UUID
    transaction_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InstallmentPlanBase(BaseModel):
    name: str
    description: Optional[str] = None
    total_amount: float
    installment_count: int = Field(gt=0)
    start_date: date
    vendor_id: Optional[UUID] = None
    tag_ids: List[UUID] = Field(default_factory=list, max_length=MAX_TAGS_PER_ENTITY)
    credit_card_id: Optional[UUID] = None
    status: InstallmentPlanStatus = InstallmentPlanStatus.active


class InstallmentPlanCreate(InstallmentPlanBase):
    @field_validator("tag_ids")
    @classmethod
    def validate_unique_tag_ids(cls, value: List[UUID]) -> List[UUID]:
        if len(set(value)) != len(value):
            raise ValueError("tag_ids must not contain duplicates")
        return value


class InstallmentPlanUpdate(BaseModel):
    """Partial update of a plan's details.

    Amounts and schedule (total_amount, installment_count, start_date) are not
    editable here: the generated installments would no longer add up. Adjust a
    single installment with PATCH /installments/{installment_id} instead.

    `description`, `vendor_id` and `credit_card_id` accept null to clear them;
    `tag_ids: null` or `[]` removes all tags.
    """

    name: Optional[str] = Field(default=None, min_length=1)
    description: Optional[str] = None
    status: Optional[InstallmentPlanStatus] = None
    vendor_id: Optional[UUID] = None
    tag_ids: Optional[List[UUID]] = Field(default=None, max_length=MAX_TAGS_PER_ENTITY)
    credit_card_id: Optional[UUID] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: Optional[str]) -> str:
        if value is None:
            raise ValueError("name cannot be null")
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("name cannot be empty")
        return cleaned

    @field_validator("status")
    @classmethod
    def validate_status(
        cls, value: Optional[InstallmentPlanStatus]
    ) -> InstallmentPlanStatus:
        if value is None:
            raise ValueError("status cannot be null")
        return value

    @field_validator("tag_ids")
    @classmethod
    def validate_unique_tag_ids(
        cls, value: Optional[List[UUID]]
    ) -> Optional[List[UUID]]:
        if value is not None and len(set(value)) != len(value):
            raise ValueError("tag_ids must not contain duplicates")
        return value


class InstallmentPlanResponse(InstallmentPlanBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    # Nested objects
    vendor: Optional[VendorResponse] = None
    tags: List[TagResponse] = Field(default_factory=list)
    # We include installments optionally to avoid massive payloads in lists
    installments: Optional[List[InstallmentResponse]] = None

    @model_validator(mode="before")
    @classmethod
    def prepare_tags(cls, data):
        if hasattr(data, "__dict__"):
            prepared = {
                field_name: getattr(data, field_name, None)
                for field_name in cls.model_fields
            }
            tags = list(getattr(data, "tags", []) or [])
            prepared["tags"] = tags
            prepared["tag_ids"] = [tag.id for tag in tags]
            return prepared
        return data

    class Config:
        from_attributes = True


class InstallmentFilters(BaseModel):
    """Filters for installment plans."""

    status: Optional[InstallmentPlanStatus] = None
    vendor_id: Optional[UUID] = None
    tag_ids: Optional[List[UUID]] = None
    tag_match: str = "all"
    credit_card_id: Optional[UUID] = None

    # Pagination
    page: int = 1
    per_page: int = 20


class InstallmentPlanListMeta(BaseModel):
    total: int
    page: int = 1
    per_page: int = 20
    has_next: bool = False
    has_previous: bool = False


class InstallmentPlanListResponse(BaseModel):
    data: List[InstallmentPlanResponse]
    meta: InstallmentPlanListMeta

    class Config:
        from_attributes = True


class LinkInstallmentRequest(BaseModel):
    """Payload for linking a transaction to a specific installment."""

    transaction_id: UUID
