"""
Authentication service layer - handles all auth business logic.
"""

from typing import Optional

from sqlalchemy.orm import Session

from app.core.auth.jwt_handler import JWTHandler
from app.domains.auth.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    RegisterResponse,
    UserInfo
)
from app.domains.refresh_tokens.service import RefreshTokenService
from app.domains.users.models import User
from app.domains.users.schemas import UserIn
from app.domains.users.service import UserService


class AuthService:
    """Service layer for authentication operations."""
    
    def __init__(self, db: Session):
        self.db = db
        self.user_service = UserService(db)
        self.refresh_token_service = RefreshTokenService(db)
    
    def login(
        self, 
        login_data: LoginRequest, 
        ip_address: Optional[str] = None
    ) -> Optional[TokenResponse]:
        """
        Authenticate user and generate tokens.
        
        Args:
            login_data: Login request with email and password
            ip_address: Client IP address for tracking
            
        Returns:
            TokenResponse with access and refresh tokens if successful, None otherwise
        """
        # Authenticate user
        user = self.user_service.authenticate_user(login_data.email, login_data.password)
        
        if not user:
            return None
        
        # Create JWT access token
        access_token = JWTHandler.create_access_token(
            user_id=user.id,
            email=user.email
        )
        
        # Create refresh token
        refresh_token = self.refresh_token_service.create_refresh_token(
            user_id=user.id,
            device_name=login_data.device_name,
            ip_address=ip_address
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token.token,
            token_type="bearer",
            expires_in=JWTHandler.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    
    def register(
        self,
        register_data: RegisterRequest,
        ip_address: Optional[str] = None
    ) -> RegisterResponse:
        """
        Register a new user and automatically log them in.
        
        Args:
            register_data: Registration request with user details
            ip_address: Client IP address for tracking
            
        Returns:
            RegisterResponse with tokens and user info
            
        Raises:
            ValueError: If email already exists
        """
        # Create user
        user_in = UserIn(
            email=register_data.email,
            password=register_data.password,
            full_name=register_data.full_name
        )
        
        user = self.user_service.create_user(user_in)
        
        # Create JWT access token
        access_token = JWTHandler.create_access_token(
            user_id=user.id,
            email=user.email
        )
        
        # Create refresh token
        refresh_token = self.refresh_token_service.create_refresh_token(
            user_id=user.id,
            device_name=register_data.device_name,
            ip_address=ip_address
        )
        
        return RegisterResponse(
            access_token=access_token,
            refresh_token=refresh_token.token,
            token_type="bearer",
            expires_in=JWTHandler.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserInfo.model_validate(user)
        )
    
    def refresh_access_token(
        self,
        refresh_token: str,
        ip_address: Optional[str] = None
    ) -> Optional[TokenResponse]:
        """
        Get a new access token using a refresh token.
        Implements refresh token rotation for security.
        
        Args:
            refresh_token: The refresh token string
            ip_address: Client IP address for tracking
            
        Returns:
            TokenResponse with new tokens if successful, None otherwise
        """
        # Rotate the refresh token
        new_refresh_token = self.refresh_token_service.rotate_refresh_token(
            old_token_string=refresh_token,
            ip_address=ip_address
        )
        
        if not new_refresh_token:
            return None
        
        # Get user information
        user = self.user_service.get_user_by_id(new_refresh_token.user_id)
        
        if not user or not user.is_active:
            return None
        
        # Create new access token
        access_token = JWTHandler.create_access_token(
            user_id=user.id,
            email=user.email
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token.token,
            token_type="bearer",
            expires_in=JWTHandler.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    
    def logout(self, refresh_token: str, user_id: str, all_devices: bool = False) -> bool:
        """
        Logout user by revoking refresh token(s).
        
        Args:
            refresh_token: The refresh token to revoke
            user_id: User ID for all-devices logout
            all_devices: Whether to logout from all devices
            
        Returns:
            True if successful, False otherwise
        """
        if all_devices:
            # Logout from all devices
            revoked_count = self.refresh_token_service.revoke_all_user_tokens(user_id)
            return revoked_count > 0
        else:
            # Logout from single device
            return self.refresh_token_service.revoke_token(refresh_token)
    
    def get_user_sessions(self, user_id: str):
        """
        Get all active sessions for a user.
        
        Args:
            user_id: The user's ID
            
        Returns:
            List of active sessions
        """
        return self.refresh_token_service.get_user_sessions(user_id)