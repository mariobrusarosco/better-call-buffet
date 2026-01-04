import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    CheckConstraint,
    Index,
    DECIMAL,
)
from sqlalchemy.dialects.postgresql import UUID

from app.db.connection_and_session import Base


class CreditCard(Base):
    __tablename__ = "credit_cards"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Credit Card Information
    name = Column(String, nullable=False)
    brand = Column(String, nullable=False)
    last_four_digits = Column(String, nullable=True)
    due_date = Column(DateTime, nullable=True)

    # Enhanced Credit Management (DECIMAL precision for financial accuracy)
    credit_limit = Column(DECIMAL(15, 2), nullable=True)
    current_balance = Column(DECIMAL(15, 2), default=Decimal("0.00"), nullable=False)
    available_credit = Column(
        DECIMAL(15, 2), nullable=True
    )  # credit_limit - current_balance

    # NEW: Balance Tracking Fields (similar to Account model)
    last_transaction_id = Column(
        UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=True
    )
    balance_updated_at = Column(DateTime, nullable=True)

    # Status Fields
    is_active = Column(Boolean, default=True, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    # Required Foreign Keys
    broker_id = Column(UUID(as_uuid=True), ForeignKey("brokers.id"), nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Database Constraints and Indexes
    __table_args__ = (
        # Unique constraint for card identification
        UniqueConstraint(
            "name", "broker_id", "account_id", name="uix_name_broker_account"
        ),
        # Performance indexes
        Index("ix_credit_cards_name", "name"),
        Index("ix_credit_cards_due_date", "due_date"),
        Index("ix_credit_cards_credit_limit", "credit_limit"),
        Index("ix_credit_cards_current_balance", "current_balance"),
        Index("ix_credit_cards_last_four", "last_four_digits"),
        Index("ix_credit_cards_active", "is_active"),
        Index("ix_credit_cards_deleted", "is_deleted"),
        Index("ix_credit_cards_brand", "brand"),
        Index("ix_credit_cards_broker", "broker_id"),
        Index("ix_credit_cards_account", "account_id"),
        Index("ix_credit_cards_balance_updated", "balance_updated_at"),
        # Balance precision constraints
        CheckConstraint(
            "credit_limit IS NULL OR (credit_limit >= 0 AND credit_limit <= 999999999999999.99)",
            name="credit_limit_precision",
        ),
        CheckConstraint(
            "current_balance >= -999999999999999.99 AND current_balance <= 999999999999999.99",
            name="current_balance_precision",
        ),
        CheckConstraint(
            "available_credit IS NULL OR (available_credit >= -999999999999999.99 AND available_credit <= 999999999999999.99)",
            name="available_credit_precision",
        ),
        # Business logic constraints
        CheckConstraint(
            "credit_limit IS NULL OR credit_limit >= 0", name="positive_credit_limit"
        ),
    )

    # Relationships - temporarily removed to avoid circular import issues
    # TODO: Add back relationships after ensuring all models are properly registered
    # broker = relationship("Broker", foreign_keys=[broker_id])
    # account = relationship("Account", foreign_keys=[account_id])
    # last_transaction = relationship("Transaction", foreign_keys=[last_transaction_id])
