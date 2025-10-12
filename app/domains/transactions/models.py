import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, CheckConstraint, DECIMAL
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.connection_and_session import Base


class Transaction(Base):
    __tablename__ = "transactions"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Core Transaction Data
    amount = Column(DECIMAL(15, 2), nullable=False)  # Changed from Float to DECIMAL for precision
    description = Column(String, nullable=False)
    date = Column(DateTime, nullable=False)
    
    # Movement Classification
    movement_type = Column(String, nullable=False)  # "income" | "expense" | "transfer" | "investment" | "reinbursement" | "other"
    category = Column(String, nullable=True)
    
    # NEW: Calculated Balance Impact (pre-calculated for performance)
    balance_impact = Column(DECIMAL(15, 2), nullable=True)
    
    # Transaction Targets (XOR + Transfer support)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True)
    credit_card_id = Column(UUID(as_uuid=True), ForeignKey("credit_cards.id"), nullable=True)
    
    # NEW: Transfer Support
    from_account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True)
    to_account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True)
    
    # Payment Linking
    related_transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=True)
    
    # Required Fields
    broker_id = Column(UUID(as_uuid=True), ForeignKey("brokers.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Status Fields
    is_paid = Column(Boolean, default=True)  # Changed default to True for consistency
    is_deleted = Column(Boolean, default=False)  # Soft delete flag
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Database Constraints (matching our migration)
    __table_args__ = (
        # Positive amounts only
        CheckConstraint('amount > 0', name='positive_amount'),
        
        # XOR constraint: exactly one target type
        CheckConstraint(
            '''(
                CASE WHEN account_id IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN credit_card_id IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN (from_account_id IS NOT NULL AND to_account_id IS NOT NULL) THEN 1 ELSE 0 END
            ) = 1''',
            name='single_transaction_target'
        ),
        
        # Prevent self-transfers
        CheckConstraint(
            'from_account_id IS NULL OR to_account_id IS NULL OR from_account_id != to_account_id',
            name='no_self_transfer'
        ),
    )

    # Relationships - temporarily removed to avoid circular import issues
    # TODO: Add back relationships after ensuring all models are properly registered
    # account = relationship("Account", foreign_keys="Transaction.account_id")
    # credit_card = relationship("CreditCard", foreign_keys="Transaction.credit_card_id")
    # broker = relationship("Broker", foreign_keys="Transaction.broker_id")
    # from_account = relationship("Account", foreign_keys="Transaction.from_account_id")
    # to_account = relationship("Account", foreign_keys="Transaction.to_account_id")
    # related_transaction = relationship("Transaction", remote_side="Transaction.id")
