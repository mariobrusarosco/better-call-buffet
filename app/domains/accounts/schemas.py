from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

# Enum for account types
class AccountType(str, Enum):
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT = "credit"
    CASH = "cash"
    INVESTMENT = "investment"
    OTHER = "other"

# Shared properties
class AccountBase(BaseModel):
    name: str
    description: Optional[str] = None
    type: AccountType
    balance: float = Field(default=0.0, ge=0.0)
    currency: str = "USD"
    is_active: bool = True

# Properties to receive via API on creation
class AccountCreate(AccountBase):
    pass

# Properties to receive via API on update
class AccountUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[AccountType] = None
    balance: Optional[float] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None

# Properties shared by models stored in DB
class AccountInDBBase(AccountBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Additional properties to return via API
class Account(AccountInDBBase):
    pass

# Account summary with minimal info
class AccountSummary(BaseModel):
    id: int
    name: str
    type: AccountType
    balance: float
    currency: str

    class Config:
        from_attributes = True
        
# Account balance history point
class BalancePoint(BaseModel):
    date: datetime
    balance: float 