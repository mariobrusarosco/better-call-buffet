from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel

# Base schema with shared properties
class BrokerBase(BaseModel):
    name: str
    description: Optional[str] = None
    website: Optional[str] = None
    is_active: bool = True

# Schema for creating a broker
class BrokerIn(BrokerBase):
    pass

# Schema for updating a broker
class BrokerUpdateIn(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    is_active: Optional[bool] = None

# Schema for database model
class BrokerInDB(BrokerBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Schema for API responses
class Broker(BrokerInDB):
    pass 