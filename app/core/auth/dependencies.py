"""
Authentication dependencies for FastAPI routes.

These dependencies are used to:
- Extract and validate JWT tokens from requests
- Get the current authenticated user
- Protect routes that require authentication
"""

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.auth.jwt_handler import JWTHandler
from app.core.auth.schemas import TokenData
from app.db.connection_and_session import get_db_session
from app.domains.users.models import User
from app.domains.users.service import UserService


# Security scheme for JWT Bearer tokens
security = HTTPBearer(
    scheme_name="JWT",
    description="JWT Bearer token authentication",
    auto_error=True  # Automatically return 401 if no token
)


async def get_current_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """
    Extract and validate JWT token from Authorization header.
    
    Args:
        credentials: The Bearer token from Authorization header
        
    Returns:
        TokenData with user information
        
    Raises:
        HTTPException: If token is invalid or expired
        
    How it works:
    1. FastAPI extracts "Bearer <token>" from Authorization header
    2. This function validates the token
    3. Returns the decoded token data
    """
    token = credentials.credentials
    
    # Validate and decode the token
    token_data = JWTHandler.decode_token(token)
    
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if it's an access token (not a refresh token)
    if token_data.token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token_data


async def get_current_user(
    token_data: TokenData = Depends(get_current_token),
    db: Session = Depends(get_db_session)
) -> User:
    """
    Get the current authenticated user from the token.
    
    Args:
        token_data: Decoded token data
        db: Database session
        
    Returns:
        The authenticated User object
        
    Raises:
        HTTPException: If user not found or inactive
        
    This is the main dependency for protected routes:
    @router.get("/protected")
    def protected_route(current_user: User = Depends(get_current_user)):
        return {"user": current_user.email}
    """
    user_service = UserService(db)
    user = user_service.get_user_by_id(token_data.user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user


async def get_current_user_id(
    token_data: TokenData = Depends(get_current_token)
) -> UUID:
    """
    Get just the user ID from the token (lighter than getting full user).
    
    Args:
        token_data: Decoded token data
        
    Returns:
        The user's UUID
        
    This is useful when you only need the user ID:
    @router.get("/my-items")
    def get_my_items(user_id: UUID = Depends(get_current_user_id)):
        return items_for_user(user_id)
    """
    return token_data.user_id


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: Session = Depends(get_db_session)
) -> Optional[User]:
    """
    Optional authentication - returns user if authenticated, None otherwise.
    
    Useful for endpoints that work both authenticated and anonymous:
    @router.get("/posts")
    def get_posts(current_user: Optional[User] = Depends(get_optional_current_user)):
        if current_user:
            # Show personalized posts
        else:
            # Show public posts
    """
    if not credentials:
        return None
    
    token_data = JWTHandler.decode_token(credentials.credentials)
    if not token_data or token_data.token_type != "access":
        return None
    
    user_service = UserService(db)
    user = user_service.get_user_by_id(token_data.user_id)
    
    if not user or not user.is_active:
        return None
    
    return user