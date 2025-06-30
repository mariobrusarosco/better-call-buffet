import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.connection_and_session import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True)
    credit_card_id = Column(
        UUID(as_uuid=True), ForeignKey("credit_cards.id"), nullable=True
    )
    broker_id = Column(UUID(as_uuid=True), ForeignKey("brokers.id"), nullable=False)
    is_paid = Column(Boolean, default=False)
    date = Column(DateTime)
    amount = Column(Float)
    description = Column(String)
    movement_type = Column(String)
    category = Column(String)

    # Foreign Keys - Add missing user_id
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Timestamps - Add missing timestamp fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Simple relationships without back_populates (can add later if needed)
    account = relationship("Account")
    credit_card = relationship("CreditCard")
    broker = relationship("Broker")
