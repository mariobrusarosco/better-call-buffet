import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    DECIMAL,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from app.db.connection_and_session import Base


class BalancePoint(Base):
    __tablename__ = "balance_points"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Core Fields
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    balance = Column(DECIMAL(15, 2), nullable=False)
    
    # Status tracking
    timeline_status = Column(String, default="current", nullable=False, server_default="current")
    
    # Gap filling
    has_transactions = Column(Boolean, default=False, nullable=False, server_default="false")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Database Constraints and Indexes
    __table_args__ = (
        # CRITICAL: One balance point per account per day
        UniqueConstraint("account_id", "date", name="uix_balance_points_account_date"),
        
        # Performance indexes
        Index("ix_balance_points_account_date", "account_id", "date"),
        Index("ix_balance_points_status", "timeline_status"),
        Index("ix_balance_points_account_status", "account_id", "timeline_status"),
        
        # Data integrity constraints
        CheckConstraint(
            "timeline_status IN ('current', 'updating', 'failed')", 
            name="ck_balance_points_valid_status"
        ),
        CheckConstraint(
            "balance >= -999999999999999.99 AND balance <= 999999999999999.99", 
            name="ck_balance_points_balance_precision"
        ),
    )
