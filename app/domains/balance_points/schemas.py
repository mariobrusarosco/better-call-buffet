from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel

class AccountPointBalanceBase(BaseModel):
    account_id: UUID
    date: datetime
    balance: float
    note: Optional[str] = None

class AccountBalancePoint(AccountPointBalanceBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class AccountBalancePointCreateRequest(AccountPointBalanceBase):
    pass

class AccountBalancePointUpdateRequest(AccountPointBalanceBase):
    pass

class AccountBalancePointResponse(AccountPointBalanceBase):
    id: UUID
    account_id: UUID
    date: datetime
    balance: float
    note: str   