from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from uuid import UUID

# Enum for account types
class AccountType(str, Enum):
    SAVINGS = "savings"
    CREDIT = "credit"
    CASH = "cash"
    INVESTMENT = "investment"
    OTHER = "other"

# Base schema with shared properties
class AccountBase(BaseModel):
    name: str
    description: Optional[str] = None
    type: AccountType
    balance: float = Field(default=0.0, ge=0.0)
    currency: str = "BRL"
    is_active: bool = True

# Schema for creating an account
class AccountIn(AccountBase):
    pass

# Schema for updating an account
class AccountUpdateIn(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[AccountType] = None
    balance: Optional[float] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None

# Schema for database model
class AccountInDB(AccountBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Schema for API responses
class Account(AccountInDB):
    pass

# Schema for account summary responses
class AccountSummary(BaseModel):
    id: UUID
    name: str
    type: AccountType
    balance: float
    currency: str

    class Config:
        from_attributes = True

# Schema for balance point responses
class BalancePoint(BaseModel):
    date: datetime
    balance: float

class AccountCreateRequest(BaseModel):
    name: str
    description: str
    type: AccountType
    balance: float
    currency: str
    is_active: bool
