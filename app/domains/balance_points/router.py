from datetime import date
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session
from app.domains.balance_points.schemas import BalancePoint
from app.domains.balance_points.service import BalancePointService

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
    Calculate balance timeline for an account (Simple Approach - Phase 1-3).

    Returns a list of balance points for each day in the date range,
    calculated on-demand from transactions. Includes gap filling for
    days with no transactions.

    **Phase**: Simple Approach - calculated, not persisted
    """
    # Validate date range
    if start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date must be before or equal to end_date"
        )

    # Calculate timeline from transactions
    service = BalancePointService(db)
    result = service.calculate_balance_timeline(
        account_id=account_id,
        user_id=current_user_id,
        start_date=start_date,
        end_date=end_date,
    )

    return result