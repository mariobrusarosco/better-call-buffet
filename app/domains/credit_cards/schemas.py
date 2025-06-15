from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# Input schemas
class CreditCardIn(BaseModel):
    account_id: UUID
    name: str
    brand: str
    due_date: datetime
    last_four_digits: str
    credit_limit: float = 0.0
    is_active: bool = True


# Response schemas
class CreditCardResponse(BaseModel):
    """Single credit card response schema"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    broker_id: UUID
    user_id: UUID
    name: str
    last_four_digits: str
    credit_limit: float = 0.0
    due_date: datetime
    is_active: bool = True
    is_deleted: bool = False


class CreditCardListMeta(BaseModel):
    total: int
    page: int = 1
    per_page: int = 20
    has_next: bool = False
    has_previous: bool = False


class CreditCardListResponse(BaseModel):
    data: List[CreditCardResponse]
    meta: CreditCardListMeta


# Future: Enhanced filtering schemas
class CreditCardFilters(BaseModel):
    is_active: Optional[bool] = None
    is_deleted: Optional[bool] = False  # Default: don't show deleted
    account_id: Optional[UUID] = None
    card_brand: Optional[str] = None
    name_contains: Optional[str] = None  # Partial name search
    due_date_month: Optional[int] = None  # Filter by due date month

    # Sorting options
    sort_by: Optional[str] = "name"  # name, balance, due_date, created_at
    sort_order: Optional[str] = "asc"  # asc, desc


class CreditCardSort(BaseModel):
    """Sorting options for credit cards"""

    field: str = "name"  # name, balance, due_date, created_at
    order: str = "asc"  # asc, desc
