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

# Schema for creating a balance point
class BalancePointIn(BalancePointBase):
    pass

# Schema for updating a balance point
class BalancePointUpdateIn(BaseModel):
    date: Optional[datetime] = None
    balance: Optional[float] = None
    note: Optional[str] = None

# Schema for database model
class BalancePointInDB(BalancePointBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Schema for API responses
class BalancePoint(BalancePointInDB):
    pass

class BalancePointCreateRequest(BalancePointBase):
    account_id: UUID
    date: datetime
    balance: float
    note: Optional[str] = None

class BalancePointUpdateRequest(BalancePointBase):
    pass

class BalancePointResponse(BalancePointBase):
    id: UUID
    account_id: UUID
    date: datetime
    balance: float
    note: str   
