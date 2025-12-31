import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    CheckConstraint,
    DECIMAL,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.connection_and_session import Base


class Transaction(Base):
    __tablename__ = "transactions"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # ==================== SIMPLE APPROACH FIELDS (Currently Active) ====================
    amount = Column(DECIMAL(15, 2), nullable=False)
    description = Column(String, nullable=False)
    date = Column(DateTime, nullable=False)
    movement_type = Column(String, nullable=False)
    category = Column(String, nullable=True)
    category_id = Column(
        UUID(as_uuid=True), ForeignKey("user_categories.id"), nullable=True
    )
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True)
    credit_card_id = Column(
        UUID(as_uuid=True), ForeignKey("credit_cards.id"), nullable=True
    )
    ignored = Column(Boolean, default=False, server_default="false", nullable=False)
    broker_id = Column(UUID(as_uuid=True), ForeignKey("brokers.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    is_paid = Column(Boolean, default=True)  # Changed default to True for consistency
    is_deleted = Column(Boolean, default=False)  # Soft delete flag
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    
    # New Fields for Vendors & Subscriptions
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=True)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=True)
    # New Fields for Installments
    installment_id = Column(UUID(as_uuid=True), ForeignKey("installments.id"), nullable=True)

    # Relationships
    category_tree = relationship("UserCategory", foreign_keys=[category_id])
    credit_card = relationship("CreditCard", foreign_keys=[credit_card_id])
    vendor = relationship("Vendor", foreign_keys=[vendor_id])
    subscription = relationship("Subscription", foreign_keys=[subscription_id])
    installment = relationship("Installment", foreign_keys=[installment_id], back_populates="transaction")
    # ===================================================================================

    # ============ COMPLEX APPROACH FIELDS (Reserved for Future Evolution) =============
    # NOTE: These fields are from the old "clean-slate-balance-architecture" plan
    # Currently UNUSED but kept for potential migration to pre-calculation approach
    # See: /docs/plans/balance-timeline-simple-to-scale.md Phase 6

    # Pre-calculated balance impact (unused - we calculate on-the-fly from amount + movement_type)
    balance_impact = Column(DECIMAL(15, 2), nullable=True)
    # Transfer support fields (unused - keeping simple for now)
    from_account_id = Column(
        UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True
    )
    to_account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True)
    # ===================================================================================
    # Payment Linking
    related_transaction_id = Column(
        UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=True
    )

    # Database Constraints (matching our migration)
    __table_args__ = (
        # XOR constraint: exactly one target type
        CheckConstraint(
            """(
                CASE WHEN account_id IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN credit_card_id IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN (from_account_id IS NOT NULL AND to_account_id IS NOT NULL) THEN 1 ELSE 0 END
            ) = 1""",
            name="single_transaction_target",
        ),
        # Prevent self-transfers
        CheckConstraint(
            "from_account_id IS NULL OR to_account_id IS NULL OR from_account_id != to_account_id",
            name="no_self_transfer",
        ),
        # Indexes
        Index("idx_transactions_account_date", "account_id", "date"),
        Index("idx_transactions_account_date_amount", "account_id", "date", "amount"),
        Index("idx_transactions_vendor_id", "vendor_id"),
        Index("idx_transactions_subscription_id", "subscription_id"),
        Index("idx_transactions_installment_id", "installment_id"),
    )

    # Relationships - temporarily removed to avoid circular import issues
    # TODO: Add back relationships after ensuring all models are properly registered
    # account = relationship("Account", foreign_keys="Transaction.account_id")
    # credit_card = relationship("CreditCard", foreign_keys="Transaction.credit_card_id")
    # broker = relationship("Broker", foreign_keys="Transaction.broker_id")
    # from_account = relationship("Account", foreign_keys="Transaction.from_account_id")
    # to_account = relationship("Account", foreign_keys="Transaction.to_account_id")
    # related_transaction = relationship("Transaction", remote_side="Transaction.id")
