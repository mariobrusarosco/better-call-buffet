from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session
from app.domains.subscriptions.schemas import UpcomingPaymentsListResponse
from app.domains.subscriptions.service import SubscriptionService
from app.domains.installments.service import InstallmentService

router = APIRouter()


@router.get("/upcoming", response_model=UpcomingPaymentsListResponse)
def get_unified_forecast(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """
    🎯 UNIFIED FORECAST ENDPOINT
    
    Returns a merged and sorted list of upcoming payments from:
    - Active Subscriptions
    - Pending Installments
    
    This is the single source of truth for the Forecast UI.
    """
    # Defaults
    if not start_date:
        start_date = date.today()
    if not end_date:
        end_date = start_date + timedelta(days=30)

    sub_service = SubscriptionService(db)
    inst_service = InstallmentService(db)

    # Fetch both
    subs = sub_service.get_upcoming_bills(current_user_id, start_date, end_date)
    insts = inst_service.get_upcoming_installments(current_user_id, start_date, end_date)

    # Merge and Sort
    all_payments = subs.data + insts.data
    all_payments.sort(key=lambda x: x.due_date)

    return UpcomingPaymentsListResponse(
        data=all_payments,
        total=len(all_payments)
    )
