import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    ForeignKey,
    String,
    Float,
    Boolean,
    DateTime,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID

from app.db.connection_and_session import Base


class CreditCard(Base):
    __tablename__ = "credit_cards"
    __table_args__ = (
        UniqueConstraint(
            "name", "broker_id", "account_id", name="uix_name_broker_account"
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, nullable=False, index=True)
    due_date = Column(DateTime, nullable=True, index=True)
    credit_limit = Column(Float, nullable=True, index=True)
    last_four_digits = Column(String, nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    brand = Column(String, nullable=False, index=True)

    # Foreign Keys
    broker_id = Column(
        UUID(as_uuid=True), ForeignKey("brokers.id"), nullable=False, index=True
    )
    account_id = Column(
        UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
