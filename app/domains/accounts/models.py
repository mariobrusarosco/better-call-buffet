from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Float, ForeignKey, Enum
import enum
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.db.base import Base

class AccountType(enum.Enum):
    SAVINGS = "savings"
    CREDIT = "credit"
    CASH = "cash"
    INVESTMENT = "investment"
    OTHER = "other"

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    type = Column(String, nullable=False)
    balance = Column(Float, default=0.0)
    currency = Column(String, default="USD")
    is_active = Column(Boolean, default=True)
    # Foreign Keys
    user_id = Column(UUID(as_uuid=True), nullable=False)
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) 

