"""
JWT Handler for creating and validating JSON Web Tokens.

Key concepts:
- Access tokens: Short-lived tokens (15-30 min) for API authentication
- Refresh tokens: Long-lived tokens (days/weeks) for getting new access tokens
- Claims: Data embedded in the token (user_id, email, expiration)
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from uuid import UUID

from jose import JWTError, jwt
from pydantic import ValidationError

from app.core.auth.schemas import TokenData
from app.core.config import settings


class JWTHandler:
    """
    Handles JWT token creation and validation.
    
    This class provides methods to:
    - Create access tokens with user claims
    - Validate and decode tokens
    - Extract user information from tokens
    """
    
    # Token configuration
    ALGORITHM = "HS256"  # HMAC with SHA-256
    ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Access tokens expire after 30 minutes
    
    @classmethod
    def create_access_token(
        cls,
        user_id: UUID,
        email: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token.
        
        Args:
            user_id: The user's ID to embed in the token
            email: The user's email to embed in the token
            expires_delta: Optional custom expiration time
            
        Returns:
            Encoded JWT token as a string
            
        Token structure (payload):
        {
            "sub": "user_id",  # Subject (user identifier)
            "email": "user@example.com",
            "exp": 1234567890,  # Expiration timestamp
            "iat": 1234567890,  # Issued at timestamp
            "type": "access"    # Token type
        }
        """
        # Calculate expiration time
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=cls.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        # Create token payload (claims)
        to_encode = {
            "sub": str(user_id),  # Subject: the user ID
            "email": email,
            "exp": expire,  # Expiration time
            "iat": datetime.utcnow(),  # Issued at
            "type": "access"  # Token type (access vs refresh)
        }
        
        # Encode the token
        encoded_jwt = jwt.encode(
            to_encode,
            settings.SECRET_KEY,  # Secret key from settings
            algorithm=cls.ALGORITHM
        )
        
        return encoded_jwt
    
    @classmethod
    def decode_token(cls, token: str) -> Optional[TokenData]:
        """
        Decode and validate a JWT token.
        
        Args:
            token: The JWT token string
            
        Returns:
            TokenData object if valid, None if invalid
            
        Validation checks:
        - Signature verification (was token tampered with?)
        - Expiration check (is token expired?)
        - Claims validation (does token have required fields?)
        """
        try:
            # Decode the token
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[cls.ALGORITHM]
            )
            
            # Extract user information
            user_id: str = payload.get("sub")
            email: str = payload.get("email")
            token_type: str = payload.get("type", "access")
            
            if user_id is None:
                return None
            
            # Create TokenData object
            token_data = TokenData(
                user_id=UUID(user_id),
                email=email,
                token_type=token_type
            )
            
            return token_data
            
        except JWTError as e:
            # Token is invalid (expired, wrong signature, malformed)
            # Log the error for debugging (in production)
            # print(f"JWT validation error: {e}")
            return None
        except (ValueError, ValidationError) as e:
            # Invalid UUID or other validation error
            # print(f"Token data validation error: {e}")
            return None
    
    @classmethod
    def verify_token(cls, token: str) -> bool:
        """
        Simple token verification (just checks if valid).
        
        Args:
            token: The JWT token string
            
        Returns:
            True if token is valid, False otherwise
        """
        return cls.decode_token(token) is not None
    
    @classmethod
    def get_token_expiry(cls, token: str) -> Optional[datetime]:
        """
        Get the expiration time of a token.
        
        Args:
            token: The JWT token string
            
        Returns:
            Expiration datetime if valid, None otherwise
        """
        try:
            # Decode without verification to get expiry
            # (useful for checking if token is close to expiring)
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[cls.ALGORITHM]
            )
            
            exp = payload.get("exp")
            if exp:
                return datetime.fromtimestamp(exp)
            
            return None
            
        except JWTError:
            return None
    
    @classmethod
    def create_tokens_pair(
        cls,
        user_id: UUID,
        email: str
    ) -> Dict[str, Any]:
        """
        Create both access and refresh tokens for a user.
        This is a convenience method for login endpoints.
        
        Args:
            user_id: The user's ID
            email: The user's email
            
        Returns:
            Dictionary with access_token and token_type
            (Refresh token is handled separately by RefreshTokenService)
        """
        access_token = cls.create_access_token(
            user_id=user_id,
            email=email
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }