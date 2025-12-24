from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class CategoryTreeNode(BaseModel):
    id: UUID
    name: str
    parent: Optional["CategoryTreeNode"] = None  # Self-referencing for parent

    class Config:
        from_attributes = True  # Allows Pydantic to read from ORM objects


class TransactionData(BaseModel):
    date: str = Field(description="Transaction date in ISO format")
    description: str = Field(description="Complete transaction description")
    amount: str = Field(
        description="Transaction amount (without sign, preserve precision)"
    )
    movement_type: str = Field(
        default="expense",
        description="Movement type: 'income' | 'expense' | 'transfer' | 'investment' | 'other'",
    )
    category: str = Field(
        default="", description="Transaction category (empty if not explicit)"
    )


class TransactionBase(BaseModel):
    account_id: Optional[UUID] = None
    credit_card_id: Optional[UUID] = None
    # Transfer support (for account-to-account transfers)
    from_account_id: Optional[UUID] = None
    to_account_id: Optional[UUID] = None
    # Core fields
    broker_id: UUID
    is_paid: bool
    date: datetime
    amount: float
    description: str
    movement_type: str
    category: str  # Legacy string field (being phased out)
    category_id: Optional[UUID] = None  # New foreign key to user_categories
    ignored: bool = False


class TransactionIn(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    date: Optional[datetime] = None

    amount: Optional[float] = None
    description: Optional[str] = None
    category: Optional[str] = None  # Legacy field
    category_id: Optional[UUID] = None  # New foreign key
    is_paid: Optional[bool] = None
    account_id: Optional[UUID] = None
    credit_card_id: Optional[UUID] = None
    movement_type: Optional[str] = None
    ignored: Optional[bool] = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v):
        """Validate that the amount is greater than 0"""
        if v is not None and v <= 0:
            raise ValueError("amount must be greater than 0")
        return v

    @field_validator("movement_type")
    @classmethod
    def validate_movement_type(cls, v):
        """Validate that the movement type is "income" or "expense"""
        if v is not None and v not in ["income", "expense"]:
            raise ValueError('movement_type must be "income" or "expense"')
        return v


class TransactionResponse(TransactionBase):
    id: UUID
    user_id: UUID
    is_deleted: bool = False
    created_at: datetime
    updated_at: datetime

    # Nested category structure (replaces category_name/parent_category_name)
    category_tree: Optional[CategoryTreeNode] = None

    @model_validator(mode="before")
    @classmethod
    def coerce_null_booleans(cls, data):
        if hasattr(data, "__dict__"):
            # ORM object - convert to dict-like access
            if getattr(data, "ignored", None) is None:
                data.ignored = False
            if getattr(data, "is_deleted", None) is None:
                data.is_deleted = False
        elif isinstance(data, dict):
            # Dict input
            if data.get("ignored") is None:
                data["ignored"] = False
            if data.get("is_deleted") is None:
                data["is_deleted"] = False
        return data

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
    category: Optional[str] = None  # Partial match
    description_contains: Optional[str] = None  # Partial match

    # Amount filters
    amount_min: Optional[float] = None
    amount_max: Optional[float] = None

    # Status filters
    is_paid: Optional[bool] = None

    # Sorting options
    sort_by: Optional[str] = "date"  # date, amount, created_at, category
    sort_order: Optional[str] = "desc"  # desc (newest first) or asc

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
    # Transfer support (for account-to-account transfers)
    from_account_id: Optional[UUID] = None
    to_account_id: Optional[UUID] = None
    # Core fields
    broker_id: UUID
    is_paid: bool
    date: datetime
    amount: float
    description: str
    movement_type: str
    category: str

    @field_validator("amount", mode="before")
    @classmethod
    def parse_amount(cls, v):
        """
        Parse amount from various formats to float.

        Handles:
        - International format: "5000.00" → 5000.0
        - Brazilian format: "5.000,00" → 5000.0 (legacy/safety)
        - Already float: 5000.0 → 5000.0
        """
        if isinstance(v, (int, float)):
            return float(v)

        if isinstance(v, str):
            # Detect format by checking if comma appears after period
            # Brazilian: "5.000,00" (period before comma)
            # International: "5,000.00" (comma before period)

            has_period = '.' in v
            has_comma = ',' in v

            if has_period and has_comma:
                # Both separators present - determine which is decimal
                period_pos = v.rfind('.')
                comma_pos = v.rfind(',')

                if comma_pos > period_pos:
                    # Brazilian: "1.234,56" → comma is decimal
                    v = v.replace(".", "").replace(",", ".")
                else:
                    # International: "1,234.56" → period is decimal
                    v = v.replace(",", "")
            elif has_comma:
                # Only comma - assume Brazilian decimal: "42,50"
                v = v.replace(",", ".")
            # If only period or neither, use as-is

            return float(v)

        return v

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


class TransactionBulkDeleteRequest(BaseModel):
    """Request schema for bulk delete operations"""

    transaction_ids: List[UUID]

    class Config:
        # Allow string UUIDs to be converted to UUID objects
        json_encoders = {UUID: str}

    @field_validator("transaction_ids", mode="before")
    @classmethod
    def parse_uuid_strings(cls, v):
        """Convert string UUIDs to UUID objects"""
        if isinstance(v, list):
            try:
                return [UUID(str(uuid_str)) for uuid_str in v]
            except ValueError as e:
                raise ValueError(f"Invalid UUID in list: {e}")
        return v

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage"""
        if self.total_submitted == 0:
            return 0.0
        return (self.total_successful / self.total_submitted) * 100
