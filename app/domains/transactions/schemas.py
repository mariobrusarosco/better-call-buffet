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


# Bulk transaction schemas
class TransactionBulkIn(BaseModel):
    """Individual transaction for bulk operations"""
    account_id: Optional[UUID] = None
    credit_card_id: Optional[UUID] = None
    broker_id: UUID
    is_paid: bool
    date: datetime
    amount: float
    description: str
    movement_type: str
    category: str
    
    def validate_xor_constraint(self) -> None:
        """Validate that exactly one of account_id or credit_card_id is provided"""
        if not self.account_id and not self.credit_card_id:
            raise ValueError("Either account_id or credit_card_id must be provided")
        if self.account_id and self.credit_card_id:
            raise ValueError("Cannot specify both account_id and credit_card_id")


class TransactionBulkRequest(BaseModel):
    """Request schema for bulk transaction creation"""
    transactions: List[TransactionBulkIn]
    
    def validate_all_constraints(self) -> None:
        """Validate XOR constraints for all transactions"""
        for i, transaction in enumerate(self.transactions):
            try:
                transaction.validate_xor_constraint()
            except ValueError as e:
                raise ValueError(f"Transaction {i}: {str(e)}")


class TransactionResult(BaseModel):
    """Result of a single transaction creation attempt"""
    success: bool
    transaction_id: Optional[UUID] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    original_data: Optional[TransactionBulkIn] = None


class TransactionBulkResponse(BaseModel):
    """Response schema for bulk transaction operations"""
    total_submitted: int
    total_successful: int
    total_failed: int
    results: List[TransactionResult]
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage"""
        if self.total_submitted == 0:
            return 0.0
        return (self.total_successful / self.total_submitted) * 100
