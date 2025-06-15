from datetime import datetime
from sqlalchemy import Column, ForeignKey, JSON, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.db.connection_and_session import Base

class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        Index('ix_invoices_user_id', 'user_id'),  # Index for faster user lookups
        Index('ix_invoices_broker_id', 'broker_id'),  # Index for broker filtering
        Index('ix_invoices_credit_card_id', 'credit_card_id'),  # Index for credit card filtering
        Index('ix_invoices_created_at', 'created_at'),  # Index for date filtering
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    credit_card_id = Column(UUID(as_uuid=True), nullable=False)  # Future: ForeignKey to credit_cards table
    broker_id = Column(UUID(as_uuid=True), ForeignKey("brokers.id"), nullable=False)
    raw_content = Column(JSON, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False) 