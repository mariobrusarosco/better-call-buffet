from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class TransactionBase(BaseModel):
    account_id: Optional[UUID] = None
    credit_card_id: Optional[UUID] = None
    broker_id: UUID
    is_paid: bool
    date: datetime
    amount: float
    description: str
    movement_type: str
    category: str


class TransactionIn(TransactionBase):
    pass


class TransactionResponse(TransactionBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# 🎓 STRUCTURED FILTERING SCHEMA
class TransactionFilters(BaseModel):
    """
    Structured filter schema for transaction queries.
    
    Benefits over individual parameters:
    - ✅ Type safety through Pydantic validation
    - ✅ Easy to extend without breaking existing code
    - ✅ Self-documenting filter capabilities
    - ✅ Consistent with other domain filtering patterns
    - ✅ Reusable across multiple service methods
    """
    # Date range filters
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    
    # Content filters
    movement_type: Optional[str] = None  # "income" or "expense"
    category: Optional[str] = None       # Partial match
    description_contains: Optional[str] = None  # Partial match
    
    # Amount filters
    amount_min: Optional[float] = None
    amount_max: Optional[float] = None
    
    # Status filters
    is_paid: Optional[bool] = None
    
    # Sorting options
    sort_by: Optional[str] = "date"      # date, amount, created_at, category
    sort_order: Optional[str] = "desc"   # desc (newest first) or asc
    
    # Pagination (embedded in filter for convenience)
    page: int = 1
    per_page: int = 20


# Pagination metadata
class TransactionListMeta(BaseModel):
    total: int
    page: int = 1
    per_page: int = 20
    has_next: bool = False
    has_previous: bool = False


# Response with pagination
class TransactionListResponse(BaseModel):
    data: List[TransactionResponse]
    meta: TransactionListMeta
