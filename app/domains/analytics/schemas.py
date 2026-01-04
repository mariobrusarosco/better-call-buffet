from decimal import Decimal
from typing import List
from pydantic import BaseModel


class MonthlyCashflow(BaseModel):
    month: str  # YYYY-MM
    income: Decimal
    expenses: Decimal
    savings: Decimal
    investments: Decimal


class CashflowSummary(BaseModel):
    total_income: Decimal
    total_expenses: Decimal
    net_cashflow: Decimal
    savings_rate: float
    monthly_data: List[MonthlyCashflow]
