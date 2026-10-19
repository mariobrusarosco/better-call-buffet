from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BalancePoint(BaseModel):
    """An account's balance on a date: a day of the calculated timeline, or a
    saved closing."""

    account_id: UUID
    date: date
    balance: Decimal

    model_config = ConfigDict(from_attributes=True)


class BalancePointUpsertIn(BaseModel):
    """Body for saving an investment account's balance on a date. Other fields
    the frontend sends (snapshot_type, note) are ignored: there is nowhere to
    store them."""

    balance: Decimal = Field(ge=0, max_digits=15, decimal_places=2)


class BalancePointResponse(BaseModel):
    id: UUID
    account_id: UUID
    date: date
    balance: Decimal
    created_at: datetime
    updated_at: datetime

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
