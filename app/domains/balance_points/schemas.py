from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator
from app.domains.balance_points.constants import TimelineStatus

from app.domains.balance_points.validators import validate_date_range_within_two_years, validate_balance_precision

# Response schema - what the API returns
class BalancePoint(BaseModel):
    """Schema for balance point responses"""
    id: UUID
    account_id: UUID
    date: date
    balance: Decimal
    timeline_status: TimelineStatus
    has_transactions: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    # Validators
    @field_validator("date")
    @classmethod
    def validate_date(cls, v: date) -> date:
        return validate_date_range_within_two_years(v)

    @field_validator("balance")
    @classmethod
    def validate_balance(cls, v: Decimal) -> Decimal:
        return validate_balance_precision(v)


# Input schemas - LEGACY (keeping for compatibility, will remove later)
class BalancePointIn(BaseModel):
    """DEPRECATED: Kept for backward compatibility during refactor"""
    account_id: UUID
    date: date
    balance: Decimal


class BalancePointUpdateIn(BaseModel):
    """DEPRECATED: Kept for backward compatibility during refactor"""
    date: Optional[date] = None
    balance: Optional[Decimal] = None


class BalancePointUpsertIn(BaseModel):
    """DEPRECATED: Kept for backward compatibility during refactor"""
    balance: Decimal


class BalanceSnapshotIn(BaseModel):
    """DEPRECATED: Kept for backward compatibility during refactor"""
    note: Optional[str] = None


# Monthly summary schema
class MonthlyBalanceSummary(BaseModel):
    """Summary of balance changes for a month"""
    month: str  # Format: "2025-01"
    month_name: str  # Format: "Jan"
    started_with: Optional[Decimal] = None
    ended_with: Optional[Decimal] = None
    movement: Decimal = Decimal("0.00")
    profit: Decimal = Decimal("0.00")
    profit_percentage: Decimal = Decimal("0.00")
    has_data: bool = False