"""Response shapes match the frontend's investments types
(financial-app/src/domains/investments/types/types-and-interfaces.ts).
In the frontend an "investment" is an account with type "investment", so
investment ids are account ids."""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class MonthlyBalanceSummary(BaseModel):
    """One month of an investment, as in the spreadsheet:

    started_with = the balance before the month (previous closing or opening)
    movement     = income − expense between those two balances
    ended_with   = the month's closing
    profit       = ended_with − started_with − movement

    Without both balances the month has no profit (`has_data` is false).
    """

    month: int  # 1-12
    year: int
    month_name: str  # "Jan"
    started_with: Optional[Decimal] = None
    ended_with: Optional[Decimal] = None
    movement: Decimal = Decimal("0.00")
    profit: Optional[Decimal] = None
    profit_percentage: float = 0.0  # 1.45 means 1.45%
    has_data: bool = False


class InvestmentResponse(BaseModel):
    id: UUID
    broker_id: UUID
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class InvestmentPortfolioResponse(BaseModel):
    """An investment since its opening. total_invested is the opening plus
    every income minus every expense; total_growth is what the market added.

    For a date range: current_balance is the balance at the end of the range,
    total_invested is the balance at its start plus what went in during it,
    total_growth is what the market added in it, and growth_percentage is each
    month's growth % (as in the spreadsheet) compounded over the range."""

    investment: InvestmentResponse
    current_balance: Decimal
    total_invested: Decimal
    total_growth: Decimal
    growth_percentage: float
    last_updated: date


class InvestmentListMeta(BaseModel):
    total: int
    total_balance: Decimal
    total_growth: Decimal
    overall_growth_percentage: float


class InvestmentListResponse(BaseModel):
    data: List[InvestmentPortfolioResponse]
    meta: InvestmentListMeta


class InvestmentBalanceResponse(BaseModel):
    """One saved balance, compared with the investment's previous one:

    movement_amount = income − expense since the previous balance
    diff_amount     = balance − previous_balance − movement_amount
    """

    id: UUID
    investment_id: UUID
    date: date
    balance: Decimal
    movement_amount: Optional[Decimal] = None
    previous_balance: Optional[Decimal] = None
    diff_amount: Decimal
    diff_percentage: float
    created_at: datetime
    updated_at: datetime


class InvestmentBalanceListMeta(BaseModel):
    total: int
    page: int
    per_page: int
    has_next: bool
    has_previous: bool


class InvestmentBalanceListResponse(BaseModel):
    data: List[InvestmentBalanceResponse]
    meta: InvestmentBalanceListMeta
