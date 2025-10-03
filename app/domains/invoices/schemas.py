from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# Credit Card Transaction
class CreditCardTransaction(BaseModel):
    id: Optional[str] = None
    date: str
    description: str
    amount: str
    category: str


# Credit Card Installment Option
class CreditCardInstallmentOption(BaseModel):
    months: int
    total: str


# Credit Card Next Due Info
class CreditCardNextDueInfo(BaseModel):
    amount: str
    balance: str


# Credit Card Raw Invoice
class CreditCardRawInvoice(BaseModel):
    total_due: str
    due_date: str
    period: str
    min_payment: str
    installment_options: List[CreditCardInstallmentOption]
    transactions: List[CreditCardTransaction]
    next_due_info: Optional[CreditCardNextDueInfo] = None


class CreditCardRawTransactionIn(BaseModel):
    date: str
    description: str
    amount: str
    category: Optional[str] = None


class CreditCardRawInvoiceIn(BaseModel):
    total_due: str
    due_date: str
    period: str
    min_payment: str
    installment_options: List[CreditCardInstallmentOption]
    transactions: List[CreditCardRawTransactionIn]
    next_due_info: Optional[CreditCardNextDueInfo] = None


# Base schema with shared properties
class InvoiceBase(BaseModel):
    credit_card_id: UUID
    raw_invoice: CreditCardRawInvoice


# Schema for creating an invoice (what frontend sends)
class InvoiceIn(BaseModel):
    credit_card_id: UUID
    raw_invoice: CreditCardRawInvoiceIn


# Schema for updating an invoice (partial fields)
class InvoiceUpdateIn(BaseModel):
    credit_card_id: Optional[UUID] = None
    raw_invoice: Optional[CreditCardRawInvoice] = None
    is_paid: Optional[bool] = None


# 🎓 STRUCTURED FILTERING SCHEMA
class InvoiceFilters(BaseModel):
    """
    Structured filter schema for invoice queries.

    Benefits over individual parameters:
    - ✅ Type safety through Pydantic validation
    - ✅ Easy to extend without breaking existing code
    - ✅ Self-documenting filter capabilities
    - ✅ Consistent with other domain filtering patterns
    - ✅ Reusable across multiple service methods
    """

    # Resource filters
    credit_card_id: Optional[UUID] = None  # Filter by specific credit card
    broker_id: Optional[UUID] = None  # Filter by specific broker

    # Status filters
    is_paid: Optional[bool] = None  # Filter by payment status
    is_deleted: Optional[bool] = False  # Include deleted invoices (default: exclude)

    # Date range filters (for created_at)
    date_from: Optional[datetime] = None  # Created after this date
    date_to: Optional[datetime] = None  # Created before this date

    # Amount filters (from raw_invoice total_due)
    amount_min: Optional[float] = None  # Minimum total due amount
    amount_max: Optional[float] = None  # Maximum total due amount

    # Period filter (from raw_invoice period)
    period_contains: Optional[str] = None  # Partial match in period field

    # Sorting options
    sort_by: Optional[str] = "created_at"  # created_at, updated_at, is_paid
    sort_order: Optional[str] = "desc"  # desc (newest first) or asc

    # Pagination (embedded in filter for convenience)
    page: int = 1
    per_page: int = 10


# Schema for API responses (what users see)
class Invoice(BaseModel):
    id: UUID
    credit_card_id: UUID
    broker_id: UUID
    raw_invoice: CreditCardRawInvoice
    is_deleted: bool
    is_paid: bool
    user_id: UUID
    # Missing fields from model
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None  
    due_date: Optional[datetime] = None
    total_amount: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Pagination metadata
class PaginationMeta(BaseModel):
    has_next: bool
    has_previous: bool
    page: int
    per_page: int
    total: int


# Response with pagination
class InvoiceListResponse(BaseModel):
    data: List[Invoice]
    meta: PaginationMeta
