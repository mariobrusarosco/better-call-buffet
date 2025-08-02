import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    CheckConstraint,
    DECIMAL,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.connection_and_session import Base


class AccountType(enum.Enum):
    SAVINGS = "savings"
    CREDIT = "credit"
    CASH = "cash"
    INVESTMENT = "investment"
    OTHER = "other"


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        Index("ix_accounts_user_id", "user_id"),  # Index for faster user lookups
        Index("ix_accounts_type", "type"),  # Index for filtering by type
        # Balance precision constraint
        CheckConstraint('balance = ROUND(balance, 2)', name='balance_precision'),
    )

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Core Account Data
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    type = Column(String, nullable=False)
    currency = Column(String, default="BRL", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Enhanced Balance Management (changed from Float to DECIMAL)
    balance = Column(DECIMAL(15, 2), default=Decimal('0.00'), nullable=False)
    available_balance = Column(DECIMAL(15, 2), default=Decimal('0.00'), nullable=False)  # For holds/pending
    
    # NEW: Balance Tracking
    last_transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=True)
    balance_updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Foreign Keys
    broker_id = Column(UUID(as_uuid=True), ForeignKey("brokers.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    broker = relationship("Broker", foreign_keys=[broker_id])
    # last_transaction = relationship("Transaction", foreign_keys=[last_transaction_id]) # Keep commented to avoid circular imports
