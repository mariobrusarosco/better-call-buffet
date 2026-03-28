"""
Authentication router - handles HTTP layer for auth endpoints.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.db.connection_and_session import get_db_session
from app.domains.auth.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserInfo
)
from app.domains.auth.service import AuthService
from app.domains.refresh_tokens.schemas import SessionInfo
from app.domains.users.models import User


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
    """
    auth_service = AuthService(db)
    
    tokens = auth_service.login(
        login_data,
        ip_address=request.client.host if request.client else None
    )
    
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return tokens


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
    """
    auth_service = AuthService(db)
    
    try:
        response = auth_service.register(
            register_data,
            ip_address=request.client.host if request.client else None
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/refresh", response_model=TokenResponse)
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
    """
    auth_service = AuthService(db)
    
    tokens = auth_service.refresh_access_token(
        refresh_data.refresh_token,
        ip_address=request.client.host if request.client else None
    )
    
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return tokens


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
    """
    auth_service = AuthService(db)
    
    success = auth_service.logout(
        refresh_token=logout_data.refresh_token,
        user_id=current_user.id,
        all_devices=logout_data.all_devices
    )
    
    if not success and not logout_data.all_devices:
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
    """
    auth_service = AuthService(db)
    sessions = auth_service.get_user_sessions(current_user.id)
    
    return [SessionInfo(**session) for session in sessions]


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """
    Revoke a specific session (logout a specific device).
    
    This feature is not yet implemented.
    """
    # Implementation would need additional method in RefreshTokenService
    # to revoke by session ID
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Feature coming soon"
    )