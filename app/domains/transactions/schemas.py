from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domains.subscriptions.schemas import SubscriptionResponse
from app.domains.tags.constants import MAX_TAGS_PER_ENTITY
from app.domains.tags.schemas import TagResponse
from app.domains.transactions.constants import MovementType
from app.domains.vendors.schemas import VendorResponse


class TransactionData(BaseModel):
    date: str = Field(description="Transaction date in ISO format")
    description: str = Field(description="Complete transaction description")
    amount: str = Field(
        description="Transaction amount (without sign, preserve precision)"
    )
    movement_type: MovementType = Field(
        default=MovementType.EXPENSE,
        description="Movement type: 'income' | 'expense' | 'transfer' | 'investment'",
    )
    tags: List[str] = Field(
        default_factory=list,
        max_length=MAX_TAGS_PER_ENTITY,
        description="Atomic tag suggestions extracted from the source document",
    )

    @field_validator("movement_type", mode="before")
    @classmethod
    def normalize_movement_type(cls, v):
        """Normalize movement type to lowercase before validation"""
        if isinstance(v, str):
            return v.lower()
        return v


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
    movement_type: MovementType = MovementType.EXPENSE
    tag_ids: List[UUID] = Field(default_factory=list, max_length=MAX_TAGS_PER_ENTITY)
    ignored: bool = False
    vendor_id: Optional[UUID] = None
    subscription_id: Optional[UUID] = None
    installment_id: Optional[UUID] = None

    @field_validator("tag_ids")
    @classmethod
    def validate_unique_tag_ids(cls, value: List[UUID]) -> List[UUID]:
        if len(set(value)) != len(value):
            raise ValueError("tag_ids must not contain duplicates")
        return value

    @field_validator("movement_type", mode="before")
    @classmethod
    def normalize_movement_type(cls, v):
        """Normalize movement type to lowercase before validation"""
        if isinstance(v, str):
            return v.lower()
        return v


class TransactionIn(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    date: Optional[datetime] = None

    amount: Optional[float] = None
    description: Optional[str] = None
    tag_ids: Optional[List[UUID]] = Field(default=None, max_length=MAX_TAGS_PER_ENTITY)
    is_paid: Optional[bool] = None
    account_id: Optional[UUID] = None
    credit_card_id: Optional[UUID] = None
    movement_type: Optional[MovementType] = None
    ignored: Optional[bool] = None
    vendor_id: Optional[UUID] = None
    subscription_id: Optional[UUID] = None
    installment_id: Optional[UUID] = None

    @field_validator("tag_ids")
    @classmethod
    def validate_unique_tag_ids(
        cls, value: Optional[List[UUID]]
    ) -> Optional[List[UUID]]:
        if value is not None and len(set(value)) != len(value):
            raise ValueError("tag_ids must not contain duplicates")
        return value

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v):
        """Validate that the amount is greater than 0"""
        if v is not None and v <= 0:
            raise ValueError("amount must be greater than 0")
        return v

    @field_validator("movement_type", mode="before")
    @classmethod
    def normalize_movement_type(cls, v):
        """Normalize movement type to lowercase before validation"""
        if isinstance(v, str):
            return v.lower()
        return v


class TransactionResponse(TransactionBase):
    id: UUID
    user_id: UUID
    is_deleted: bool = False
    created_at: datetime
    updated_at: datetime
    account_name: Optional[str] = None
    credit_card_name: Optional[str] = None

    tags: List[TagResponse] = Field(default_factory=list)
    vendor: Optional[VendorResponse] = None
    subscription: Optional[SubscriptionResponse] = None

    @model_validator(mode="before")
    @classmethod
    def prepare_transaction_data(cls, data):
        """
        Prepare transaction data from ORM objects or dicts.

        Responsibilities:
        1. Set default values for nullable boolean fields
        2. Extract readable account/card names for UI display
        3. Extract account_id from credit_card relationship (for credit card transactions)
        """
        if hasattr(data, "__dict__"):
            # ORM object from database query
            prepared_data = {
                field_name: getattr(data, field_name, None)
                for field_name in cls.model_fields
            }

            # 1. Set default boolean values
            if prepared_data["ignored"] is None:
                prepared_data["ignored"] = False
            if prepared_data["is_deleted"] is None:
                prepared_data["is_deleted"] = False

            # 2. Extract readable names from eager-loaded relationships
            if hasattr(data, "account") and data.account:
                prepared_data["account_name"] = data.account.name

            if hasattr(data, "credit_card") and data.credit_card:
                prepared_data["credit_card_name"] = data.credit_card.name

                if hasattr(data.credit_card, "account") and data.credit_card.account:
                    prepared_data["account_name"] = data.credit_card.account.name

            # 3. Extract account_id from credit_card JOIN
            if hasattr(data, "credit_card") and data.credit_card:
                prepared_data["account_id"] = data.credit_card.account_id

            prepared_data["tags"] = list(getattr(data, "tags", []) or [])
            prepared_data["tag_ids"] = [tag.id for tag in prepared_data["tags"]]

            return prepared_data

        elif isinstance(data, dict):
            # Dict input (for testing or manual construction)

            # 1. Set default boolean values
            if data.get("ignored") is None:
                data["ignored"] = False
            if data.get("is_deleted") is None:
                data["is_deleted"] = False

            # 2. Populate readable names when nested objects are already present
            account = data.get("account")
            if account and data.get("account_name") is None:
                if isinstance(account, dict):
                    data["account_name"] = account.get("name")
                else:
                    data["account_name"] = getattr(account, "name", None)

            credit_card = data.get("credit_card")
            if credit_card and data.get("credit_card_name") is None:
                if isinstance(credit_card, dict):
                    data["credit_card_name"] = credit_card.get("name")
                else:
                    data["credit_card_name"] = getattr(credit_card, "name", None)

            tags = data.get("tags") or []
            if data.get("tag_ids") is None:
                data["tag_ids"] = [
                    tag.get("id") if isinstance(tag, dict) else getattr(tag, "id", None)
                    for tag in tags
                ]

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
    movement_type: Optional[List[MovementType]] = None  # "income", "expense", etc.
    tag_ids: Optional[List[UUID]] = None
    exclude_tag_ids: Optional[List[UUID]] = None
    tag_match: Literal["all", "any"] = "all"
    description_contains: Optional[str] = None  # Partial match

    # Amount filters
    amount_min: Optional[float] = None
    amount_max: Optional[float] = None

    # Status filters
    is_paid: Optional[bool] = None
    # True: linked to an installment; False: not linked. Independent of is_paid,
    # which users can also set by hand.
    has_installment: Optional[bool] = None

    # Vendor & Subscription filters
    vendor_id: Optional[UUID] = None
    subscription_id: Optional[UUID] = None

    # Sorting options
    sort_by: Optional[str] = "date"  # date, amount, created_at
    sort_order: Optional[str] = "desc"  # desc (newest first) or asc

    # Pagination (embedded in filter for convenience)
    page: int = 1
    per_page: int = 20

    @field_validator("movement_type", mode="before")
    @classmethod
    def normalize_movement_type_list(cls, v):
        """Normalize list of movement types to lowercase"""
        if v is None:
            return v
        if isinstance(v, list):
            return [item.lower() if isinstance(item, str) else item for item in v]
        return v


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
    movement_type: MovementType = MovementType.EXPENSE
    tag_ids: List[UUID] = Field(default_factory=list, max_length=MAX_TAGS_PER_ENTITY)

    @field_validator("tag_ids")
    @classmethod
    def validate_unique_tag_ids(cls, value: List[UUID]) -> List[UUID]:
        if len(set(value)) != len(value):
            raise ValueError("tag_ids must not contain duplicates")
        return value

    @field_validator("movement_type", mode="before")
    @classmethod
    def normalize_movement_type(cls, v):
        """Normalize movement type to lowercase before validation"""
        if isinstance(v, str):
            return v.lower()
        return v

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

            has_period = "." in v
            has_comma = "," in v

            if has_period and has_comma:
                # Both separators present - determine which is decimal
                period_pos = v.rfind(".")
                comma_pos = v.rfind(",")

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


class TransactionBulkUpdate(BaseModel):
    """Apply the same partial update to a bounded set of transactions."""

    transaction_ids: List[UUID] = Field(min_length=1, max_length=100)
    changes: TransactionUpdate

    @model_validator(mode="after")
    def validate_bulk_update(self):
        if len(set(self.transaction_ids)) != len(self.transaction_ids):
            raise ValueError("transaction_ids must not contain duplicates")

        if not self.changes.model_fields_set:
            raise ValueError("changes must contain at least one field")

        return self


class TransactionBulkUpdateResponse(BaseModel):
    """The authoritative state of transactions updated atomically."""

    updated_count: int
    transactions: List[TransactionResponse]


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
