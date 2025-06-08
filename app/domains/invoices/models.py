from sqlalchemy import Column, ForeignKey, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.db.connection_and_session import Base

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    credit_card_id = Column(UUID(as_uuid=True), nullable=False)  # No FK constraint yet
    broker_id = Column(UUID(as_uuid=True), ForeignKey("brokers.id"), nullable=False)
    raw_content = Column(JSON, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False) 