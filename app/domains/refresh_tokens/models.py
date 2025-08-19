import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.connection_and_session import Base


class RefreshToken(Base):
    """
    Refresh token model for managing long-lived authentication tokens.
    
    Key concepts:
    - Refresh tokens are used to obtain new access tokens
    - They have longer expiration times than access tokens
    - Can be revoked for security (logout, suspicious activity)
    - One user can have multiple refresh tokens (multiple devices)
    """
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("ix_refresh_tokens_token", "token", unique=True),
        Index("ix_refresh_tokens_user_id", "user_id"),
        Index("ix_refresh_tokens_expires_at", "expires_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # The actual refresh token string (hashed for security)
    token = Column(String, nullable=False, unique=True)
    
    # Link to the user who owns this token
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Token metadata
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    
    # Optional: Track device/client info
    device_name = Column(String, nullable=True)  # e.g., "Chrome on Windows"
    ip_address = Column(String, nullable=True)   # IP address when token was created
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)  # Track when token was last used
    revoked_at = Column(DateTime, nullable=True)     # When the token was revoked
    
    # Relationship to User
    user = relationship("User", backref="refresh_tokens")