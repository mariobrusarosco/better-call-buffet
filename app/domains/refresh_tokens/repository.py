from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.domains.refresh_tokens.models import RefreshToken


class RefreshTokenRepository:
    """
    Repository layer for RefreshToken data access.
    Handles all database operations for refresh tokens.
    """

    def __init__(self, db: Session):
        self.db = db

    def create(self, token_data: dict) -> RefreshToken:
        """Create a new refresh token"""
        refresh_token = RefreshToken(**token_data)
        self.db.add(refresh_token)
        self.db.commit()
        self.db.refresh(refresh_token)
        return refresh_token

    def get_by_token(self, token: str) -> Optional[RefreshToken]:
        """Get refresh token by token string"""
        return self.db.query(RefreshToken).filter(
            RefreshToken.token == token
        ).first()

    def get_valid_token(self, token: str) -> Optional[RefreshToken]:
        """
        Get a valid (not expired, not revoked) refresh token.
        This is the main method used for token validation.
        """
        return self.db.query(RefreshToken).filter(
            and_(
                RefreshToken.token == token,
                RefreshToken.is_revoked == False,
                RefreshToken.expires_at > datetime.utcnow()
            )
        ).first()

    def get_user_tokens(self, user_id: UUID, only_valid: bool = True) -> List[RefreshToken]:
        """Get all refresh tokens for a user"""
        query = self.db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id
        )
        
        if only_valid:
            query = query.filter(
                and_(
                    RefreshToken.is_revoked == False,
                    RefreshToken.expires_at > datetime.utcnow()
                )
            )
        
        return query.all()

    def revoke_token(self, token: RefreshToken) -> RefreshToken:
        """Revoke a refresh token"""
        token.is_revoked = True
        token.revoked_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(token)
        return token

    def revoke_all_user_tokens(self, user_id: UUID) -> int:
        """Revoke all refresh tokens for a user"""
        count = self.db.query(RefreshToken).filter(
            and_(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked == False
            )
        ).update({
            "is_revoked": True,
            "revoked_at": datetime.utcnow()
        })
        self.db.commit()
        return count

    def update_last_used(self, token: RefreshToken) -> RefreshToken:
        """Update the last_used_at timestamp"""
        token.last_used_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(token)
        return token

    def delete_expired_tokens(self) -> int:
        """Delete all expired tokens (cleanup job)"""
        count = self.db.query(RefreshToken).filter(
            RefreshToken.expires_at <= datetime.utcnow()
        ).delete()
        self.db.commit()
        return count

    def delete_revoked_tokens(self, days_old: int = 30) -> int:
        """Delete revoked tokens older than specified days"""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        count = self.db.query(RefreshToken).filter(
            and_(
                RefreshToken.is_revoked == True,
                RefreshToken.revoked_at <= cutoff_date
            )
        ).delete()
        self.db.commit()
        return count