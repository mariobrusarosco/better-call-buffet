import secrets
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.domains.refresh_tokens.models import RefreshToken
from app.domains.refresh_tokens.repository import RefreshTokenRepository


class RefreshTokenService:
    """
    Service layer for RefreshToken business logic.
    Handles token generation, validation, and rotation.
    """
    
    # Token configuration
    TOKEN_LENGTH = 64  # Length of the random token string
    TOKEN_EXPIRY_DAYS = 30  # Refresh tokens expire after 30 days
    
    def __init__(self, db: Session):
        self.repository = RefreshTokenRepository(db)
    
    def create_refresh_token(
        self, 
        user_id: UUID,
        device_name: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> RefreshToken:
        """
        Create a new refresh token for a user.
        
        Args:
            user_id: The user's ID
            device_name: Optional device/browser information
            ip_address: Optional IP address
            
        Returns:
            The created refresh token
        """
        # Generate a secure random token
        token_string = secrets.token_urlsafe(self.TOKEN_LENGTH)
        
        # Calculate expiration date
        expires_at = datetime.utcnow() + timedelta(days=self.TOKEN_EXPIRY_DAYS)
        
        # Create token data
        token_data = {
            "token": token_string,
            "user_id": user_id,
            "expires_at": expires_at,
            "device_name": device_name,
            "ip_address": ip_address,
            "is_revoked": False
        }
        
        return self.repository.create(token_data)
    
    def validate_refresh_token(self, token_string: str) -> Optional[RefreshToken]:
        """
        Validate a refresh token and return it if valid.
        
        Args:
            token_string: The refresh token string
            
        Returns:
            The refresh token if valid, None otherwise
        """
        token = self.repository.get_valid_token(token_string)
        
        if token:
            # Update last used timestamp
            self.repository.update_last_used(token)
            
        return token
    
    def rotate_refresh_token(
        self, 
        old_token_string: str,
        device_name: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Optional[RefreshToken]:
        """
        Rotate a refresh token (revoke old, create new).
        This is a security best practice - when a refresh token is used,
        it should be replaced with a new one.
        
        Args:
            old_token_string: The current refresh token
            device_name: Optional updated device information
            ip_address: Optional updated IP address
            
        Returns:
            New refresh token if rotation successful, None otherwise
        """
        # Validate the old token
        old_token = self.repository.get_valid_token(old_token_string)
        if not old_token:
            return None
        
        # Revoke the old token
        self.repository.revoke_token(old_token)
        
        # Create a new token for the same user
        return self.create_refresh_token(
            user_id=old_token.user_id,
            device_name=device_name or old_token.device_name,
            ip_address=ip_address or old_token.ip_address
        )
    
    def revoke_token(self, token_string: str) -> bool:
        """
        Revoke a specific refresh token (used for logout).
        
        Args:
            token_string: The refresh token to revoke
            
        Returns:
            True if token was revoked, False if not found
        """
        token = self.repository.get_by_token(token_string)
        if not token:
            return False
        
        self.repository.revoke_token(token)
        return True
    
    def revoke_all_user_tokens(self, user_id: UUID) -> int:
        """
        Revoke all refresh tokens for a user (logout from all devices).
        
        Args:
            user_id: The user's ID
            
        Returns:
            Number of tokens revoked
        """
        return self.repository.revoke_all_user_tokens(user_id)
    
    def get_user_sessions(self, user_id: UUID) -> List[dict]:
        """
        Get all active sessions (valid refresh tokens) for a user.
        Useful for showing "logged in devices" to the user.
        
        Args:
            user_id: The user's ID
            
        Returns:
            List of session information
        """
        tokens = self.repository.get_user_tokens(user_id, only_valid=True)
        
        return [
            {
                "id": str(token.id),
                "device_name": token.device_name,
                "ip_address": token.ip_address,
                "created_at": token.created_at.isoformat(),
                "last_used_at": token.last_used_at.isoformat() if token.last_used_at else None,
            }
            for token in tokens
        ]
    
    def cleanup_expired_tokens(self) -> dict:
        """
        Clean up expired and old revoked tokens.
        This should be run periodically (e.g., daily cron job).
        
        Returns:
            Dictionary with cleanup statistics
        """
        expired_count = self.repository.delete_expired_tokens()
        revoked_count = self.repository.delete_revoked_tokens(days_old=7)
        
        return {
            "expired_deleted": expired_count,
            "revoked_deleted": revoked_count,
            "total_deleted": expired_count + revoked_count
        }