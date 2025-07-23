import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Column, 
    DateTime, 
    ForeignKey, 
    Index, 
    String, 
    CheckConstraint,
    DECIMAL,
    Boolean,
)
from sqlalchemy.dialects.postgresql import UUID

from app.db.connection_and_session import Base


class BalancePoint(Base):
    __tablename__ = "balance_points"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Enhanced Balance Snapshot Data (DECIMAL precision for financial accuracy)
    balance = Column(DECIMAL(15, 2), nullable=False)
    available_balance = Column(DECIMAL(15, 2), nullable=True)  # For accounts with holds/pending
    
    # NEW: Enhanced Tracking Fields
    snapshot_type = Column(String, nullable=False)  # "daily", "transaction", "manual", "reconciliation"
    source_transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)  # For reconciliation validation
    
    # Balance Target (XOR: either account_id OR credit_card_id)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=True)
    credit_card_id = Column(UUID(as_uuid=True), ForeignKey("credit_cards.id", ondelete="CASCADE"), nullable=True)
    
    # Snapshot Information
    date = Column(DateTime, nullable=False)
    note = Column(String, nullable=True)
    
    # Required Fields
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Database Constraints and Indexes
    __table_args__ = (
        # Performance indexes
        Index("ix_balance_points_account_id", "account_id"),
        Index("ix_balance_points_credit_card_id", "credit_card_id"),
        Index("ix_balance_points_date", "date"),
        Index("ix_balance_points_snapshot_type", "snapshot_type"),
        Index("ix_balance_points_user_date", "user_id", "date"),
        Index("ix_balance_points_verified", "is_verified"),
        Index("ix_balance_points_source_transaction", "source_transaction_id"),
        
        # Balance precision constraints
        CheckConstraint('balance >= -999999999999999.99 AND balance <= 999999999999999.99', name='balance_precision'),
        CheckConstraint('available_balance IS NULL OR (available_balance >= -999999999999999.99 AND available_balance <= 999999999999999.99)', name='available_balance_precision'),
        
        # XOR constraint: exactly one of account_id or credit_card_id must be set
        CheckConstraint(
            '''(
                CASE WHEN account_id IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN credit_card_id IS NOT NULL THEN 1 ELSE 0 END
            ) = 1''',
            name='single_balance_target'
        ),
        
        # Valid snapshot types
        CheckConstraint(
            "snapshot_type IN ('daily', 'transaction', 'manual', 'reconciliation')",
            name='valid_snapshot_type'
        ),
    )

    # Relationships - temporarily removed to avoid circular import issues
    # TODO: Add back relationships after ensuring all models are properly registered
    # account = relationship("Account", foreign_keys=[account_id])
    # credit_card = relationship("CreditCard", foreign_keys=[credit_card_id])
    # source_transaction = relationship("Transaction", foreign_keys=[source_transaction_id])
