from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.connection_and_session import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID, primary_key=True, default=uuid4)
    account_id = Column(UUID, ForeignKey("accounts.id"))
    credit_card_id = Column(UUID, ForeignKey("credit_cards.id"))

    broker_id = Column(UUID, ForeignKey("brokers.id"))
    is_paid = Column(Boolean, default=False)
    date = Column(DateTime)
    amount = Column(Float)
    description = Column(String)
    movement_type = Column(String)
    category = Column(String)

    # Simple relationships without back_populates (can add later if needed)
    account = relationship("Account")
    credit_card = relationship("CreditCard")
    broker = relationship("Broker")
