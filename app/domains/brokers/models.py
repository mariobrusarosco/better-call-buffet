import uuid
from datetime import datetime

from sqlalchemy import ARRAY, Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from app.db.connection_and_session import Base


class Broker(Base):
    __tablename__ = "brokers"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    colors = Column(ARRAY(String), nullable=False)
    logo = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
