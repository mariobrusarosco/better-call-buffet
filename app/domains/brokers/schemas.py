from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel

# Base schema with shared properties
class BrokerBase(BaseModel):
    name: str
    description: Optional[str] = None
    

# Schema for creating a broker (user input - no user_id required)
class BrokerIn(BrokerBase):
    name: str
    description: Optional[str] = None
    colors: list[str]
    logo: str

# Schema for updating a broker (user input - no user_id required)
class BrokerUpdateIn(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    colors: Optional[list[str]] = None
    logo: Optional[str] = None

# Schema for creating broker in database (includes user_id)
class BrokerCreate(BrokerIn):
    user_id: UUID

# Schema for updating broker in database (includes user_id for filtering)
class BrokerUpdate(BrokerUpdateIn):
    user_id: UUID

# Schema for database model (full representation)
class BrokerInDB(BrokerBase):
    id: UUID
    user_id: UUID
    is_active: bool
    colors: list[str]
    logo: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Schema for API responses (what users see)
class Broker(BrokerInDB):
    pass 