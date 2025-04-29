from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Float, ForeignKey, Enum, Index
import enum
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.db.base import Base

class AccountType(enum.Enum):
    SAVINGS = "savings"
    CREDIT = "credit"
    CASH = "cash"
    INVESTMENT = "investment"
    OTHER = "other"

class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        Index('ix_accounts_user_id', 'user_id'),  # Index for faster user lookups
        Index('ix_accounts_type', 'type'),  # Index for filtering by type
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    type = Column(String, nullable=False)
    balance = Column(Float, default=0.0, nullable=False)
    currency = Column(String, default="BRL", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    # Foreign Keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False) 

