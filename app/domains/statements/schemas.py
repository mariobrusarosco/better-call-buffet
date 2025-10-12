from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

# Import transaction schema from transactions domain
from app.domains.transactions.schemas import TransactionData


# ============================================================================
# SHARED MODELS
# ============================================================================

# StatementTransaction is now replaced by TransactionData from transactions domain


# ============================================================================
# BANK STATEMENT SCHEMAS (Account statements only)
# ============================================================================

class RawBankStatement(BaseModel):
    """Raw bank account statement data - NO credit card fields"""
    period: str
    opening_balance: str = ""
    closing_balance: str = ""  # Made optional for backward compatibility
    transactions: List[TransactionData]


# ============================================================================
# CREDIT CARD INVOICE SCHEMAS (Credit card invoices only)
# ============================================================================

class NextDueInfo(BaseModel):
    """Next payment due information for credit cards"""
    amount: str
    balance: str


class InstallmentOption(BaseModel):
    """Credit card installment option"""
    months: int
    total: str


class RawCreditCardInvoice(BaseModel):
    """Raw credit card invoice data - NO bank statement fields"""
    period: str
    total_due: str
    due_date: str
    min_payment: str
    installment_options: List[InstallmentOption] = []
    next_due_info: Optional[NextDueInfo] = None
    transactions: List[TransactionData]



# Input schema for creating bank statements
class StatementIn(BaseModel):
    """Input for creating a bank account statement"""
    account_id: UUID
    raw_statement: RawBankStatement  # Use specialized bank statement schema!


# Response schema for bank statements
class StatementResponse(BaseModel):
    """Response for bank account statement"""
    id: UUID
    account_id: UUID
    user_id: UUID
    
    # Bank statement specific fields
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    opening_balance: Optional[str] = None
    closing_balance: Optional[str] = None
    
    # Raw data (uses specialized bank statement schema)
    raw_statement: RawBankStatement
    
    # Status fields
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