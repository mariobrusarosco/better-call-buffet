from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class RefreshTokenBase(BaseModel):
    """Base schema for refresh tokens"""
    device_name: Optional[str] = Field(None, description="Device or browser name")
    ip_address: Optional[str] = Field(None, description="IP address when token was created")


class RefreshTokenCreate(RefreshTokenBase):
    """Schema for creating a refresh token (internal use)"""
    user_id: UUID


class RefreshTokenInfo(BaseModel):
    """Schema for displaying refresh token information to users"""
    id: UUID
    device_name: Optional[str]
    ip_address: Optional[str]
    created_at: datetime
    last_used_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class SessionInfo(BaseModel):
    """Schema for user session information"""
    id: str
    device_name: Optional[str]
    ip_address: Optional[str]
    created_at: str
    last_used_at: Optional[str]