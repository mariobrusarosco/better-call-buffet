from datetime import date, datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from app.domains.vendors.schemas import VendorResponse
from app.domains.categories.schemas import CategoryResponse


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
    category_id: Optional[UUID] = None
    credit_card_id: Optional[UUID] = None
    status: InstallmentPlanStatus = InstallmentPlanStatus.active


class InstallmentPlanCreate(InstallmentPlanBase):
    pass


class InstallmentPlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    total_amount: Optional[float] = None
    status: Optional[InstallmentPlanStatus] = None
    vendor_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    credit_card_id: Optional[UUID] = None


class InstallmentPlanResponse(InstallmentPlanBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    
    # Nested objects
    vendor: Optional[VendorResponse] = None
    category: Optional[CategoryResponse] = None
    # We include installments optionally to avoid massive payloads in lists
    installments: Optional[List[InstallmentResponse]] = None

    class Config:
        from_attributes = True


class InstallmentFilters(BaseModel):
    """Filters for installment plans."""
    status: Optional[InstallmentPlanStatus] = None
    vendor_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
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
