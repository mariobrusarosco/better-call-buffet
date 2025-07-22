import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from app.db.connection_and_session import Base


class Statement(Base):
    __tablename__ = "statements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Statement period information
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)
    
    # Financial summary
    total_due = Column(String, nullable=True)  # Keep as string to preserve formatting like "7.287,10"
    min_payment = Column(String, nullable=True)
    opening_balance = Column(String, nullable=True)
    closing_balance = Column(String, nullable=True)
    
    # Raw statement data (JSON)
    raw_statement = Column(JSON, nullable=False)
    
    # Status tracking
    is_processed = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    account = relationship("Account")