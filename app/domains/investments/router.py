from datetime import date
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session
from app.domains.investments.schemas import (
    InvestmentPortfolioResponse,
    MonthlyBalanceSummary,
)
from app.domains.investments.service import InvestmentService

router = APIRouter()

MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"


def first_day_of(month: str) -> date:
    year, month_number = month.split("-")
    return date(int(year), int(month_number), 1)


def get_investment_service(db: Session = Depends(get_db_session)) -> InvestmentService:
    return InvestmentService(db)


@router.get("/portfolio", response_model=InvestmentPortfolioResponse)
def get_portfolio(
    from_month: str = Query(..., alias="from", pattern=MONTH_PATTERN),
    to_month: str = Query(..., alias="to", pattern=MONTH_PATTERN),
    user_id: UUID = Depends(get_current_user_id),
    service: InvestmentService = Depends(get_investment_service),
):
    """Every active investment account month by month (balance, movement,
    profit, %), plus the portfolio totals for each month."""
    return service.get_portfolio(
        user_id, first_day_of(from_month), first_day_of(to_month)
    )


@router.get("/{account_id}/monthly", response_model=List[MonthlyBalanceSummary])
def get_monthly_performance(
    account_id: UUID,
    from_month: str = Query(..., alias="from", pattern=MONTH_PATTERN),
    to_month: str = Query(..., alias="to", pattern=MONTH_PATTERN),
    user_id: UUID = Depends(get_current_user_id),
    service: InvestmentService = Depends(get_investment_service),
):
    """One investment account month by month: start, movement, closing,
    profit and %."""
    return service.get_monthly_performance(
        account_id, user_id, first_day_of(from_month), first_day_of(to_month)
    )
