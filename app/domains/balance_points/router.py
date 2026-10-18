from datetime import date
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session
from app.domains.balance_points.schemas import BalancePoint, BalancePointUpsertIn
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


@router.put("/{account_id}/{closing_date}", response_model=BalancePoint)
def save_closing(
    account_id: UUID,
    closing_date: date,
    closing_in: BalancePointUpsertIn,
    current_user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db_session),
):
    """
    Record an investment account's balance at the end of `closing_date` (for a
    monthly closing, the last day of the month). Saving the same date again
    replaces the value.
    """
    service = BalancePointService(db)
    return service.save_closing(
        account_id, current_user_id, closing_date, closing_in.balance
    )


@router.delete("/{account_id}/{closing_date}", status_code=status.HTTP_204_NO_CONTENT)
def delete_closing(
    account_id: UUID,
    closing_date: date,
    current_user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db_session),
):
    """Remove a closing. The opening balance can't be deleted."""
    BalancePointService(db).delete_closing(account_id, current_user_id, closing_date)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
