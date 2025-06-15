from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Column, String, Index
from sqlalchemy.dialects.postgresql import UUID
from app.db.connection_and_session import Base
import uuid


class BalancePoint(Base):
    __tablename__ = "balance_points"
    __table_args__ = (
        Index("ix_balance_points_account_id", "account_id"),
        Index("ix_balance_points_date", "date"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    date = Column(DateTime, nullable=False)
    balance = Column(Float, nullable=False)
    note = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
