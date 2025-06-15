from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel


# Base schema with shared properties
class BalancePointBase(BaseModel):
    account_id: UUID
    date: datetime
    balance: float
    note: Optional[str] = None


# Schema for creating a balance point (what frontend sends)
class BalancePointIn(BalancePointBase):
    pass


# Schema for updating a balance point (partial fields)
class BalancePointUpdateIn(BaseModel):
    date: Optional[datetime] = None
    balance: Optional[float] = None
    note: Optional[str] = None


# Schema for API responses (what users see)
class BalancePoint(BalancePointBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
