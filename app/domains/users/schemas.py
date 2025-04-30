from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, EmailStr

# Base schema with shared properties
class UserBase(BaseModel):
    email: EmailStr
    name: str
    is_active: bool = True

# Schema for creating a user
class UserIn(UserBase):
    pass

# Schema for updating a user
class UserUpdateIn(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    is_active: Optional[bool] = None

# Schema for database model
class UserInDB(UserBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Schema for API responses
class User(UserInDB):
    pass

# Schema for user summary responses (minimal info)
class UserSummary(BaseModel):
    id: UUID
    name: str
    email: EmailStr

    class Config:
        from_attributes = True 