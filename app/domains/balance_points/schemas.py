from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# ============================================================================
# SIMPLE APPROACH SCHEMAS (Phase 1-3)
# These schemas support calculated balance timelines (no database persistence)
# ============================================================================

class BalancePoint(BaseModel):
    """
    Calculated balance point response (Simple Approach).

    This represents a balance at a specific date, calculated on-demand
    from transactions. NOT saved to database.
    """
    account_id: UUID
    date: date
    balance: Decimal

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# COMPLEX APPROACH SCHEMAS (Phase 5-6 - Reserved for Future)
# These will be used IF we migrate to pre-calculated, saved balance points
# Currently UNUSED - keeping for potential future evolution
# ============================================================================

class BalancePointIn(BaseModel):
    """RESERVED: For future pre-calculation approach (Phase 5-6)"""
    account_id: UUID
    date: date
    balance: Decimal


class BalancePointUpdateIn(BaseModel):
    """RESERVED: For future pre-calculation approach (Phase 5-6)"""
    date: Optional[date] = None
    balance: Optional[Decimal] = None


class BalancePointUpsertIn(BaseModel):
    """RESERVED: For future pre-calculation approach (Phase 5-6)"""
    balance: Decimal


class BalanceSnapshotIn(BaseModel):
    """RESERVED: For future snapshot feature (Phase 5-6)"""
    note: Optional[str] = None


class MonthlyBalanceSummary(BaseModel):
    """RESERVED: For future monthly summary feature"""
    month: str  # Format: "2025-01"
    month_name: str  # Format: "Jan"
    started_with: Optional[Decimal] = None
    ended_with: Optional[Decimal] = None
    movement: Decimal = Decimal("0.00")
    profit: Decimal = Decimal("0.00")
    profit_percentage: Decimal = Decimal("0.00")
    has_data: bool = False