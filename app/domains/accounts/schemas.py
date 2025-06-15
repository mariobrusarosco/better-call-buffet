from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from uuid import UUID
from app.domains.brokers.schemas import Broker


# Enum for account types
class AccountType(str, Enum):
    SAVINGS = "savings"
    CREDIT = "credit"
    CASH = "cash"
    INVESTMENT = "investment"
    OTHER = "other"


# Base schema with shared properties (used for input)
class AccountBase(BaseModel):
    name: str
    description: Optional[str] = None
    type: AccountType
    balance: float = Field(default=0.0, ge=0.0)
    currency: str = "BRL"
    broker_id: UUID  # Keep broker_id for input validation
    is_active: bool = True


# Schema for creating/updating an account
class AccountIn(AccountBase):
    pass


# Schema for updating an account
class AccountUpdateIn(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[AccountType] = None
    balance: Optional[float] = None
    currency: Optional[str] = None
    broker_id: Optional[UUID] = None
    is_active: Optional[bool] = None


# Internal schema for database operations
class AccountWithBroker(AccountBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    broker: Broker

    class Config:
        from_attributes = True


# Schema for API responses (excludes broker_id since we include the full broker object)
class Account(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    type: AccountType
    balance: float
    currency: str
    is_active: bool
    broker: Broker
    user_id: UUID

    class Config:
        from_attributes = True


# Simplified response schema (excludes timestamps)
class AccountResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    type: AccountType
    balance: float
    currency: str
    is_active: bool
    broker: Broker
    user_id: UUID

    class Config:
        from_attributes = True
