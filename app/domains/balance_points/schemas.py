from datetime import date
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
    """Body for saving an investment account's closing on a date."""

    balance: Decimal = Field(ge=0, max_digits=15, decimal_places=2)


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
