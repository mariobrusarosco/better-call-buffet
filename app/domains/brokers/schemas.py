from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


# Base schema with shared properties
class BrokerBase(BaseModel):
    name: str
    description: Optional[str] = None
    colors: list[str]
    logo: str
    is_active: bool = True


# Schema for creating a broker (what frontend sends)
class BrokerIn(BrokerBase):
    pass


# Schema for updating a broker (partial fields)
class BrokerUpdateIn(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    colors: Optional[list[str]] = None
    logo: Optional[str] = None


# Schema for API responses (what users see)
class Broker(BrokerBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
