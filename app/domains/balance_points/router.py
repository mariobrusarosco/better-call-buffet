from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session
from app.domains.balance_points.schemas import (
    BalancePoint,
    BalancePointIn,
    BalancePointUpdateIn,
    BalancePointUpsertIn,
    MonthlyBalanceSummary,
)
from app.domains.balance_points.service import BalancePointService

router = APIRouter()


@router.post("", response_model=BalancePoint)
def create_balance_point(
    balance_point_in: BalancePointIn,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Create a new balance point"""
    service = BalancePointService(db)
    try:
        return service.create_balance_point(
            balance_point_in=balance_point_in, user_id=current_user_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/account/{account_id}/date/{target_date}", response_model=BalancePoint)
def upsert_balance_point(
    account_id: UUID,
    target_date: datetime,
    balance_data: BalancePointUpsertIn,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """
    Create or update a balance point for a specific account and date.
    
    If a balance point already exists for this account and date, it will be updated.
    If not, a new balance point will be created.
    
    This is useful for:
    - Setting daily balance snapshots
    - Updating existing balance records
    - Ensuring only one balance point per day per account
    """
    service = BalancePointService(db)
    try:
        # Convert Pydantic model to dict
        balance_dict = balance_data.model_dump()
        
        return service.upsert_balance_point(
            account_id=account_id,
            target_date=target_date,
            balance_data=balance_dict,
            user_id=current_user_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/account/{account_id}", response_model=List[BalancePoint])
def get_balance_points_by_account_id(
    account_id: UUID,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get all balance points for a specific account"""
    service = BalancePointService(db)
    try:
        return service.get_balance_points_by_account_id(
            account_id=account_id, user_id=current_user_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{balance_point_id}", response_model=BalancePoint)
def get_balance_point_by_id(
    balance_point_id: UUID,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get a specific balance point by ID"""
    service = BalancePointService(db)
    balance_point = service.get_balance_point_by_id(balance_point_id, current_user_id)
    if not balance_point:
        raise HTTPException(status_code=404, detail="Balance point not found")
    return balance_point


@router.put("/{balance_point_id}", response_model=BalancePoint)
def update_balance_point(
    balance_point_id: UUID,
    update_data: BalancePointUpdateIn,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Update a balance point"""
    service = BalancePointService(db)
    try:
        # Convert Pydantic model to dict, excluding None values
        update_dict = update_data.model_dump(exclude_none=True)
        balance_point = service.update_balance_point(
            balance_point_id, current_user_id, update_dict
        )
        if not balance_point:
            raise HTTPException(status_code=404, detail="Balance point not found")
        return balance_point
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{balance_point_id}")
def delete_balance_point(
    balance_point_id: UUID,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Delete a balance point"""
    service = BalancePointService(db)
    if not service.delete_balance_point(balance_point_id, current_user_id):
        raise HTTPException(status_code=404, detail="Balance point not found")
    return {"message": "Balance point deleted successfully"}


@router.get("/history/movements")
def get_balance_history_with_movements(
    account_id: Optional[UUID] = Query(None, description="Filter by specific account"),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """
    Get balance history with calculated movements (DIFF functionality).
    Shows the difference between consecutive balance points.
    """
    service = BalancePointService(db)
    return service.get_balance_history_with_movements(current_user_id, account_id)


@router.get("/account/{account_id}/trend", response_model=List[BalancePoint])
def get_account_balance_trend(
    account_id: UUID,
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get balance trend for an account over specified days"""
    service = BalancePointService(db)
    try:
        return service.get_balance_trend(account_id, current_user_id, days)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/account/{account_id}/monthly-summary", response_model=List[MonthlyBalanceSummary])
def get_monthly_balance_summaries(
    account_id: UUID,
    year: Optional[int] = Query(None, description="Year to get summaries for (defaults to current year)"),
    months: int = Query(12, ge=1, le=12, description="Number of months to return (max 12)"),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """
    Get monthly balance summaries for an account.
    
    Returns for each month:
    - started_with: First balance of the month
    - ended_with: Last balance of the month
    - movement: Net change during the month (ended - started)
    - profit: Same as movement
    - profit_percentage: Percentage change from start of month
    - has_data: Whether balance points exist for that month
    
    Perfect for displaying monthly financial performance cards.
    """
    service = BalancePointService(db)
    try:
        summaries = service.get_monthly_summaries(account_id, current_user_id, year, months)
        return [MonthlyBalanceSummary(**summary) for summary in summaries]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/account/{account_id}/latest", response_model=BalancePoint)
def get_latest_balance_point(
    account_id: UUID,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get the most recent balance point for an account"""
    service = BalancePointService(db)
    try:
        balance_point = service.get_latest_balance_by_account(
            account_id, current_user_id
        )
        if not balance_point:
            raise HTTPException(
                status_code=404, detail="No balance points found for this account"
            )
        return balance_point
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/date-range", response_model=List[BalancePoint])
def get_balance_points_by_date_range(
    start_date: datetime = Query(..., description="Start date (ISO format)"),
    end_date: datetime = Query(..., description="End date (ISO format)"),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get balance points within a date range across all accounts"""
    service = BalancePointService(db)
    try:
        return service.get_balance_points_by_date_range(
            current_user_id, start_date, end_date
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/total-balance/at-date")
def get_total_balance_at_date(
    target_date: date = Query(
        ..., description="Date to calculate balance for (YYYY-MM-DD)"
    ),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Calculate total balance across all accounts at a specific date"""
    service = BalancePointService(db)
    total_balance = service.get_total_balance_at_date(current_user_id, target_date)
    return {
        "date": target_date,
        "total_balance": total_balance,
        "currency": "BRL",  # You might want to make this configurable
    }
