"""
Authentication schemas for request/response models.
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Schema for login request"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    device_name: Optional[str] = Field(None, description="Device or browser name for tracking")


class TokenResponse(BaseModel):
    """
    Schema for token response after successful authentication.
    
    This is what the client receives after login:
    - access_token: JWT token to use in Authorization header
    - refresh_token: Token to get new access tokens
    - token_type: Always "bearer" for JWT
    - expires_in: Access token expiration in seconds
    """
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="Refresh token for getting new access tokens")
    token_type: str = Field(default="bearer", description="Token type (always 'bearer')")
    expires_in: int = Field(default=1800, description="Access token expiration time in seconds")


class RefreshRequest(BaseModel):
    """Schema for refresh token request"""
    refresh_token: str = Field(..., description="The refresh token")


class TokenData(BaseModel):
    """
    Schema for decoded token data.
    This is what we extract from a valid JWT token.
    """
    user_id: UUID = Field(..., description="User ID from token")
    email: Optional[str] = Field(None, description="User email from token")
    token_type: str = Field(default="access", description="Type of token (access/refresh)")


class LogoutRequest(BaseModel):
    """Schema for logout request"""
    refresh_token: str = Field(..., description="Refresh token to revoke")
    all_devices: bool = Field(default=False, description="Logout from all devices")


class RegisterRequest(BaseModel):
    """Schema for user registration request"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    full_name: Optional[str] = Field(None, description="User's full name")
    device_name: Optional[str] = Field(None, description="Device or browser name for tracking")


class RegisterResponse(TokenResponse):
    """Schema for registration response - includes tokens and user info"""
    user: "UserInfo" = Field(..., description="Created user information")


class UserInfo(BaseModel):
    """Schema for authenticated user information"""
    id: UUID
    email: str
    full_name: Optional[str]
    is_active: bool
    
    class Config:
        from_attributes = True