from datetime import date
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session
from app.domains.analytics.service import AnalyticsService
from app.domains.analytics.repository import AnalyticsRepository
from app.domains.analytics.schemas import CashflowSummary

router = APIRouter()


def get_analytics_service(db: Session = Depends(get_db_session)) -> AnalyticsService:
    return AnalyticsService(AnalyticsRepository(db))


@router.get("/cashflow", response_model=CashflowSummary)
def get_cashflow_analytics(
    date_from: date,
    date_to: date,
    account_id: Optional[UUID] = None,
    user_id: UUID = Depends(get_current_user_id),
    service: AnalyticsService = Depends(get_analytics_service),
):
    """
    Get aggregated cashflow data (income, expenses, savings, investments) for a specific date range.
    Returns monthly breakdown and total summary.
    """
    return service.get_cashflow_analytics(
        user_id=user_id, date_from=date_from, date_to=date_to, account_id=account_id
    )
