from datetime import date
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session
from app.domains.balance_points.schemas import (
    BalancePoint,
    BalancePointResponse,
    BalancePointUpsertIn,
)
from app.domains.balance_points.service import BalancePointService
from app.domains.investments.schemas import MonthlyBalanceSummary
from app.domains.investments.service import InvestmentService

router = APIRouter()


@router.get("/{account_id}/timeline")
def get_balance_timeline(
    account_id: UUID,
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    current_user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db_session),
) -> List[BalancePoint]:
    """
    End-of-day balance for each day in the range, calculated on demand from
    the account's opening, closings and transactions.
    """
    # Validate date range
    if start_date > end_date:
        raise HTTPException(
            status_code=400, detail="start_date must be before or equal to end_date"
        )

    service = BalancePointService(db)
    result = service.calculate_balance_timeline(
        account_id=account_id,
        user_id=current_user_id,
        start_date=start_date,
        end_date=end_date,
    )

    return result


@router.put(
    "/account/{account_id}/date/{point_date}", response_model=BalancePointResponse
)
def save_balance_point(
    account_id: UUID,
    point_date: date,
    balance_in: BalancePointUpsertIn,
    current_user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db_session),
):
    """
    Save an investment account's balance at the end of `point_date` (for a
    monthly balance, the last day of the month). Saving the same date again
    replaces the value. On an account without an opening balance, the first
    one saved becomes the opening.
    """
    service = BalancePointService(db)
    return service.save_closing(
        account_id, current_user_id, point_date, balance_in.balance
    )


@router.get(
    "/account/{account_id}/monthly-summary",
    response_model=List[MonthlyBalanceSummary],
)
def get_monthly_summary(
    account_id: UUID,
    year: int = Query(default_factory=lambda: date.today().year, ge=1900, le=9999),
    months: int = Query(12, ge=1, le=12, description="January to this month"),
    current_user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db_session),
):
    """An investment account month by month: started with, movement, ended
    with, profit and %."""
    return InvestmentService(db).get_monthly_summary(
        account_id, current_user_id, year, months
    )
