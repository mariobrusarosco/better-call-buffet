from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


# Transaction within a statement
class StatementTransaction(BaseModel):
    date: str  # Keep as string to preserve original format like "07/04/2025"
    description: str
    amount: str  # Keep as string to preserve formatting like "-202,06"
    category: str = ""


# Next due information
class NextDueInfo(BaseModel):
    amount: str
    balance: str


# Raw statement structure (matches your payload)
class RawStatement(BaseModel):
    total_due: str
    due_date: str
    period: str
    min_payment: str
    installment_options: List[Any] = []  # Can be empty array or specific structure later
    transactions: List[StatementTransaction]
    next_due_info: NextDueInfo


# Input schema for creating statements
class StatementIn(BaseModel):
    account_id: UUID
    raw_statement: RawStatement


# Response schema
class StatementResponse(BaseModel):
    id: UUID
    account_id: UUID
    user_id: UUID
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    due_date: Optional[datetime] = None
    total_due: Optional[str] = None
    min_payment: Optional[str] = None
    opening_balance: Optional[str] = None
    closing_balance: Optional[str] = None
    raw_statement: RawStatement
    is_processed: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Filtering schema for statements
class StatementFilters(BaseModel):
    account_id: Optional[UUID] = None
    is_processed: Optional[bool] = None
    is_deleted: Optional[bool] = False
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    sort_by: Optional[str] = "created_at"
    sort_order: Optional[str] = "desc"
    page: int = 1
    per_page: int = 20


# Pagination metadata
class StatementListMeta(BaseModel):
    total: int
    page: int = 1
    per_page: int = 20
    has_next: bool = False
    has_previous: bool = False


# Response with pagination
class StatementListResponse(BaseModel):
    data: List[StatementResponse]
    meta: StatementListMeta