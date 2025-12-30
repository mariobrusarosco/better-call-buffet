from datetime import date, datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel
from app.domains.vendors.schemas import VendorResponse
from app.domains.categories.schemas import CategoryResponse


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
    category_id: Optional[UUID] = None
    is_active: bool = True


class SubscriptionCreate(SubscriptionBase):
    pass


class SubscriptionUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    billing_cycle: Optional[BillingCycle] = None
    next_due_date: Optional[date] = None
    vendor_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class SubscriptionResponse(SubscriptionBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    
    # Computed status
    is_paid_this_cycle: bool = False
    
    # Nested objects
    vendor: Optional[VendorResponse] = None
    category: Optional[CategoryResponse] = None

    class Config:
        from_attributes = True


class SubscriptionFilters(BaseModel):
    is_active: Optional[bool] = None
    vendor_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    
    # Pagination
    page: int = 1
    per_page: int = 20


class SubscriptionListMeta(BaseModel):
    total: int
    page: int = 1
    per_page: int = 20
    has_next: bool = False
    has_previous: bool = False


class SubscriptionListResponse(BaseModel):
    data: List[SubscriptionResponse]
    meta: SubscriptionListMeta

    class Config:
        from_attributes = True


class LinkPaymentRequest(BaseModel):
    transaction_id: UUID


class UpcomingPaymentResponse(BaseModel):
    """Represents a single projected future subscription payment."""
    subscription_id: UUID
    subscription_name: str
    vendor: Optional[VendorResponse] = None # Changed from vendor_name to nested VendorResponse
    amount: float
    due_date: date


class UpcomingPaymentsListResponse(BaseModel):
    """List of all projected future subscription payments."""
    data: List[UpcomingPaymentResponse]
    total: int