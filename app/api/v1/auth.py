"""
Authentication endpoints for JWT-based authentication.

This module provides:
- POST /auth/login - Login with email/password
- POST /auth/refresh - Get new access token using refresh token
- POST /auth/logout - Revoke refresh token
- GET /auth/me - Get current user information
- GET /auth/sessions - List user's active sessions
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.auth.jwt_handler import JWTHandler
from app.core.auth.schemas import (
    LoginRequest,
    LogoutRequest, 
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserInfo
)
from app.db.connection_and_session import get_db_session
from app.domains.refresh_tokens.schemas import SessionInfo
from app.domains.refresh_tokens.service import RefreshTokenService
from app.domains.users.models import User
from app.domains.users.schemas import UserIn
from app.domains.users.service import UserService


router = APIRouter()


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    login_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db_session)
):
    """
    Login with email and password to get JWT tokens.
    
    **Flow:**
    1. Validate email/password
    2. Create JWT access token (short-lived)
    3. Create refresh token (long-lived, stored in database)
    4. Return both tokens to client
    
    **Client Usage:**
    ```
    POST /auth/login
    {
        "email": "user@example.com",
        "password": "userpassword",
        "device_name": "Chrome on Windows"  // optional
    }
    ```
    
    **Response:**
    ```
    {
        "access_token": "eyJ...",
        "refresh_token": "abc123...",
        "token_type": "bearer",
        "expires_in": 1800
    }
    ```
    """
    # Authenticate user
    user_service = UserService(db)
    user = user_service.authenticate_user(login_data.email, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create JWT access token
    access_token = JWTHandler.create_access_token(
        user_id=user.id,
        email=user.email
    )
    
    # Create refresh token
    refresh_token_service = RefreshTokenService(db)
    refresh_token = refresh_token_service.create_refresh_token(
        user_id=user.id,
        device_name=login_data.device_name,
        ip_address=request.client.host if request.client else None
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token.token,
        token_type="bearer",
        expires_in=JWTHandler.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds
    )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    register_data: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db_session)
):
    """
    Register a new user and automatically log them in.
    
    **Flow:**
    1. Validate registration data
    2. Create new user account
    3. Automatically authenticate the new user
    4. Create JWT access token and refresh token
    5. Return tokens and user information
    
    **Client Usage:**
    ```
    POST /auth/register
    {
        "email": "user@example.com",
        "password": "userpassword",
        "full_name": "John Doe",  // optional
        "device_name": "Chrome on Windows"  // optional
    }
    ```
    
    **Response:**
    ```
    {
        "access_token": "eyJ...",
        "refresh_token": "abc123...",
        "token_type": "bearer",
        "expires_in": 1800,
        "user": {
            "id": "uuid-string",
            "email": "user@example.com",
            "full_name": "John Doe",
            "is_active": true
        }
    }
    ```
    """
    # Create user
    user_service = UserService(db)
    user_in = UserIn(
        email=register_data.email,
        password=register_data.password,
        full_name=register_data.full_name
    )
    
    try:
        user = user_service.create_user(user_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Create JWT access token
    access_token = JWTHandler.create_access_token(
        user_id=user.id,
        email=user.email
    )
    
    # Create refresh token
    refresh_token_service = RefreshTokenService(db)
    refresh_token = refresh_token_service.create_refresh_token(
        user_id=user.id,
        device_name=register_data.device_name,
        ip_address=request.client.host if request.client else None
    )
    
    return RegisterResponse(
        access_token=access_token,
        refresh_token=refresh_token.token,
        token_type="bearer",
        expires_in=JWTHandler.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserInfo.model_validate(user)
    )


@router.post("/refresh", response_model=dict)
async def refresh_token(
    refresh_data: RefreshRequest,
    request: Request,
    db: Session = Depends(get_db_session)
):
    """
    Get a new access token using a refresh token.
    
    **Flow:**
    1. Validate refresh token
    2. Create new JWT access token
    3. Optionally rotate refresh token (create new, revoke old)
    4. Return new access token
    
    **Security Note:** 
    This implements refresh token rotation - each time you use a refresh token,
    you get a new one. This helps detect token theft.
    
    **Client Usage:**
    ```
    POST /auth/refresh
    {
        "refresh_token": "abc123..."
    }
    ```
    """
    refresh_token_service = RefreshTokenService(db)
    
    # Rotate the refresh token (get new one, revoke old one)
    new_refresh_token = refresh_token_service.rotate_refresh_token(
        old_token_string=refresh_data.refresh_token,
        ip_address=request.client.host if request.client else None
    )
    
    if not new_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user information for the new access token
    user_service = UserService(db)
    user = user_service.get_user_by_id(new_refresh_token.user_id)
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new access token
    access_token = JWTHandler.create_access_token(
        user_id=user.id,
        email=user.email
    )
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token.token,
        "token_type": "bearer",
        "expires_in": JWTHandler.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    logout_data: LogoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """
    Logout by revoking refresh token(s).
    
    **Options:**
    - Single device logout: Revoke the provided refresh token
    - All devices logout: Revoke all refresh tokens for the user
    
    **Client Usage:**
    ```
    POST /auth/logout
    Authorization: Bearer <access_token>
    {
        "refresh_token": "abc123...",
        "all_devices": false  // true to logout from all devices
    }
    ```
    """
    refresh_token_service = RefreshTokenService(db)
    
    if logout_data.all_devices:
        # Logout from all devices
        revoked_count = refresh_token_service.revoke_all_user_tokens(current_user.id)
        # Return info about how many tokens were revoked (optional)
        return {"message": f"Logged out from {revoked_count} devices"}
    else:
        # Logout from single device
        success = refresh_token_service.revoke_token(logout_data.refresh_token)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid refresh token"
            )


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user information.
    
    This endpoint demonstrates how to use JWT authentication
    to protect routes and access user information.
    
    **Client Usage:**
    ```
    GET /auth/me
    Authorization: Bearer <access_token>
    ```
    """
    return UserInfo.model_validate(current_user)


@router.get("/sessions", response_model=List[SessionInfo])
async def get_user_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """
    Get all active sessions (devices) for the current user.
    
    This shows all places where the user is logged in,
    which is useful for security management.
    
    **Client Usage:**
    ```
    GET /auth/sessions
    Authorization: Bearer <access_token>
    ```
    
    **Response:**
    ```
    [
        {
            "id": "uuid-string",
            "device_name": "Chrome on Windows",
            "ip_address": "192.168.1.100",
            "created_at": "2023-01-01T12:00:00Z",
            "last_used_at": "2023-01-01T15:30:00Z"
        }
    ]
    ```
    """
    refresh_token_service = RefreshTokenService(db)
    sessions = refresh_token_service.get_user_sessions(current_user.id)
    
    return [SessionInfo(**session) for session in sessions]


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """
    Revoke a specific session (logout a specific device).
    
    **Client Usage:**
    ```
    DELETE /auth/sessions/{session_id}
    Authorization: Bearer <access_token>
    ```
    """
    # Implementation would need additional method in RefreshTokenService
    # to revoke by session ID - left as an exercise
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Feature coming soon"
    )