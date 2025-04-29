from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Float, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.db.base import Base

class Investment(Base):
    __tablename__ = "investments"
    __table_args__ = (
        Index('ix_investments_user_id', 'user_id'),  # Index for faster user lookups
        Index('ix_investments_account_id', 'account_id'),  # Index for account lookups
        Index('ix_investments_broker_id', 'broker_id'),  # Index for broker lookups
        Index('ix_investments_symbol', 'symbol'),  # Index for symbol lookups
    )

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    quantity = Column(Float, default=0.0, nullable=False)
    current_price = Column(Float, default=0.0, nullable=False)
    currency = Column(String, default="BRL", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Foreign Keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    broker_id = Column(Integer, ForeignKey("brokers.id", ondelete="SET NULL"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class InvestmentBalancePoint(Base):
    __tablename__ = "investment_balance_points"
    __table_args__ = (
        Index('ix_investment_balance_points_investment_id', 'investment_id'),  # Index for investment lookups
        Index('ix_investment_balance_points_date', 'date'),  # Index for date filtering
    )

    id = Column(Integer, primary_key=True, index=True)
    investment_id = Column(Integer, ForeignKey("investments.id", ondelete="CASCADE"), nullable=False)
    date = Column(DateTime, nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    total_value = Column(Float, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False) 