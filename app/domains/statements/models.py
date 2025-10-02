import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from app.db.connection_and_session import Base


class Statement(Base):
    """
    Bank Account Statement Model
    
    Stores parsed bank account statements (NOT credit card invoices).
    Credit card invoices are stored in the 'invoices' table.
    """
    __tablename__ = "statements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Bank statement period information
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)
    
    # Bank statement financial summary
    opening_balance = Column(String, nullable=True)  # Starting balance
    closing_balance = Column(String, nullable=True)  # Ending balance
    
    # Raw statement data (JSON) - stores RawBankStatement schema
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