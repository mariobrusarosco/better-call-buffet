from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List
from enum import Enum

# Enum for investment types - matching your SQLAlchemy enum
class InvestmentType(str, Enum):
    RENDA_FIXA = "renda_fixa"
    RENDA_VARIAVEL = "renda_variavel"
    MUTUAL_FUND = "fundo_de_investimento"
    ETF = "etf"
    CRYPTO = "cripto"
    PREVIDENCIA = "previdencia"

# Base Pydantic model
class InvestmentBase(BaseModel):
    name: str
    description: Optional[str] = None
    type: str
    amount: float
    currency: str

# For creating a new investment
class InvestmentCreate(InvestmentBase):
    pass

# For updating an investment
class InvestmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[str] = None

# For returning investment data
class Investment(InvestmentBase):
    id: int
    broker_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Investment balance point model
class InvestmentBalancePointBase(BaseModel):
    investment_id: int
    date: datetime
    balance: float
    movement: Optional[float] = None

class InvestmentBalancePointCreate(InvestmentBalancePointBase):
    pass

class InvestmentBalancePoint(InvestmentBalancePointBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True 