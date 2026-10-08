from datetime import date, datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domains.tags.constants import MAX_TAGS_PER_ENTITY
from app.domains.tags.schemas import TagResponse
from app.domains.vendors.schemas import VendorResponse


class BillingCycle(str, Enum):
    weekly = "weekly"
    monthly = "monthly"
    quarterly = "quarterly"
    yearly = "yearly"


class SubscriptionBase(BaseModel):
    name: str
    amount: float
    billing_cycle: BillingCycle
    next_due_date: date
    vendor_id: Optional[UUID] = None
    tag_ids: List[UUID] = Field(default_factory=list, max_length=MAX_TAGS_PER_ENTITY)
    is_active: bool = True


class SubscriptionCreate(SubscriptionBase):
    @field_validator("tag_ids")
    @classmethod
    def validate_unique_tag_ids(cls, value: List[UUID]) -> List[UUID]:
        if len(set(value)) != len(value):
            raise ValueError("tag_ids must not contain duplicates")
        return value


class SubscriptionUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    billing_cycle: Optional[BillingCycle] = None
    next_due_date: Optional[date] = None
    vendor_id: Optional[UUID] = None
    tag_ids: Optional[List[UUID]] = Field(default=None, max_length=MAX_TAGS_PER_ENTITY)
    is_active: Optional[bool] = None

    @field_validator("tag_ids")
    @classmethod
    def validate_unique_tag_ids(
        cls, value: Optional[List[UUID]]
    ) -> Optional[List[UUID]]:
        if value is not None and len(set(value)) != len(value):
            raise ValueError("tag_ids must not contain duplicates")
        return value


class SubscriptionResponse(SubscriptionBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    # Computed status
    is_paid_this_cycle: bool = False

    # Nested objects
    vendor: Optional[VendorResponse] = None
    tags: List[TagResponse] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def prepare_tags(cls, data):
        if hasattr(data, "__dict__"):
            # Copy only attributes that actually exist on the ORM model. Inserting
            # None for response-only fields would override their Pydantic defaults.
            missing = object()
            prepared = {}
            for field_name in cls.model_fields:
                value = getattr(data, field_name, missing)
                if value is not missing:
                    prepared[field_name] = value
            tags = list(getattr(data, "tags", []) or [])
            prepared["tags"] = tags
            prepared["tag_ids"] = [tag.id for tag in tags]
            return prepared
        return data

    class Config:
        from_attributes = True


class SubscriptionFilters(BaseModel):
    is_active: Optional[bool] = None
    vendor_id: Optional[UUID] = None
    tag_ids: Optional[List[UUID]] = None
    tag_match: str = "all"

    # Pagination
    page: int = 1
    per_page: int = 20


class TagBreakdownItem(BaseModel):
    name: str
    amount: float


class MonthlyForecastItem(BaseModel):
    month: str
    amount: float


class SubscriptionSummary(BaseModel):
    monthly_burn_rate: float
    yearly_projection: float
    due_next_30_days: float
    active_count: int
    tag_breakdown: List[TagBreakdownItem]
    monthly_forecast: List[MonthlyForecastItem]


class SubscriptionListMeta(BaseModel):
    total: int
    page: int = 1
    per_page: int = 20
    has_next: bool = False
    has_previous: bool = False
    summary: Optional[SubscriptionSummary] = None


class SubscriptionListResponse(BaseModel):
    data: List[SubscriptionResponse]
    meta: SubscriptionListMeta

    class Config:
        from_attributes = True


class LinkPaymentRequest(BaseModel):
    transaction_id: UUID


class UpcomingPaymentResponse(BaseModel):
    """Represents a single projected future payment (Subscription or Installment)."""

    id: UUID  # Original Subscription ID or Installment ID
    name: str  # Subscription name or Plan name
    vendor: Optional[VendorResponse] = None
    amount: float
    due_date: date
    source_type: str = "subscription"  # "subscription" or "installment"


class UpcomingPaymentsListResponse(BaseModel):
    """List of all projected future subscription payments."""

    data: List[UpcomingPaymentResponse]
    total: int
