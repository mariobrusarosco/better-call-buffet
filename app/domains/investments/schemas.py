from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from app.domains.brokers.schemas import Broker


class MonthlyBalanceSummary(BaseModel):
    """One month of an investment, as in the spreadsheet:

    started_with = previous month's closing
    movement     = signed total of the month's transactions (income − expense)
    ended_with   = this month's closing
    profit       = ended_with − started_with − movement

    Without both closings the month has no profit (`has_data` is false).
    """

    month: str  # "2025-01"
    month_name: str  # "Jan"
    started_with: Optional[Decimal] = None
    ended_with: Optional[Decimal] = None
    movement: Decimal = Decimal("0.00")
    profit: Optional[Decimal] = None
    profit_percentage: Optional[Decimal] = None  # 1.45 means 1.45%
    has_data: bool = False


class InvestmentAccountPerformance(BaseModel):
    account_id: UUID
    name: str
    broker: Broker
    months: List[MonthlyBalanceSummary]


class InvestmentPortfolioResponse(BaseModel):
    """Every active investment account month by month, plus one totals row
    per month. A total's profit_percentage is total profit ÷ total closing."""

    accounts: List[InvestmentAccountPerformance]
    totals: List[MonthlyBalanceSummary]
