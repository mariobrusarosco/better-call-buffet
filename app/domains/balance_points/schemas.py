from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


# Base schema with shared properties
class BalancePointBase(BaseModel):
    account_id: UUID
    date: datetime
    balance: float
    snapshot_type: str = "manual"  # Default to manual for user-created balance points
    note: Optional[str] = None


# Schema for creating a balance point (what frontend sends)
class BalancePointIn(BalancePointBase):
    pass


# Schema for updating a balance point (partial fields)
class BalancePointUpdateIn(BaseModel):
    date: Optional[datetime] = None
    balance: Optional[float] = None
    snapshot_type: Optional[str] = None
    note: Optional[str] = None


# Schema for API responses (what users see)
class BalancePoint(BalancePointBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Schema for upserting a balance point (create or update)
class BalancePointUpsertIn(BaseModel):
    balance: float
    snapshot_type: str = "manual"
    note: Optional[str] = None


# Schema for simple balance snapshot creation (no balance input needed)
class BalanceSnapshotIn(BaseModel):
    note: Optional[str] = None


# Schema for monthly balance summary
class MonthlyBalanceSummary(BaseModel):
    month: str  # Format: "2025-01"
    month_name: str  # Format: "Jan"
    started_with: Optional[float] = None
    ended_with: Optional[float] = None
    movement: float = 0.0
    profit: float = 0.0
    profit_percentage: float = 0.0
    has_data: bool = False
