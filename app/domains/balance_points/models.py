import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Date,
    DECIMAL,
    Boolean,
    String,
    UniqueConstraint,
    Index,
    CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from app.db.connection_and_session import Base
from app.domains.balance_points.constants import TimelineStatus


class BalancePoint(Base):
    __tablename__ = "balance_points"
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    # Foreign Keys
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    # Core Data
    date = Column(Date, nullable=False)
    balance = Column(DECIMAL(15, 2), nullable=False)
    timeline_status = Column(String, default=TimelineStatus.CURRENT, nullable=False)
    has_transactions = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("account_id", "date", name="uix_balance_points_account_date"),
        CheckConstraint("timeline_status IN ('current', 'updating', 'failed')", name="ck_valid_timeline_status"),
        Index("ix_balance_points_account_date", "account_id", "date"),
        Index("ix_balance_points_status", "timeline_status"),
        Index("ix_balance_points_account_status", "account_id", "timeline_status"),
    )

    def __repr__(self):
        return f"<BalancePoint {self.id} for account {self.account_id} on {self.date}>"
