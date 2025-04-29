from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base import Base


class Investment(Base):
    __tablename__ = "investments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    type = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user_id = Column(UUID(as_uuid=True), nullable=False)
    # We'll add broker_id back when we create the brokers table
    # broker_id = Column(Integer, ForeignKey("brokers.id"))

class InvestmentType(Enum):
    RENDA_FIXA = "renda_fixa"
    RENDA_VARIAVEL = "renda_variavel"
    MUTUAL_FUND = "fundo_de_investimento"
    ETF = "etf"
    CRYPTO = "cripto"
    PREVIDENCIA = "previdencia"


class InvestmentBalancePoint(Base):
    __tablename__ = "investment_balance_points"
    
    id = Column(Integer, primary_key=True, index=True)
    investment_id = Column(Integer, ForeignKey("investments.id"))
    date = Column(DateTime, nullable=False)
    balance = Column(Float, nullable=False)
    movement = Column(Float, nullable=True)  # Optional movement amount
    created_at = Column(DateTime, default=datetime.utcnow)

