from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session
from app.domains.cashflow.schemas import CashflowSummary
from app.domains.cashflow.service import CashflowService
from app.domains.cashflow.views.router import router as views_router

router = APIRouter()
router.include_router(views_router, prefix="/views")


def get_cashflow_service(db: Session = Depends(get_db_session)) -> CashflowService:
    return CashflowService(db)


@router.get("", response_model=CashflowSummary)
def get_monthly_cashflow(
    date_from: date,
    date_to: date,
    account_id: Optional[UUID] = None,
    user_id: UUID = Depends(get_current_user_id),
    service: CashflowService = Depends(get_cashflow_service),
):
    """
    Get aggregated cashflow data (income, expenses, savings) for a specific date range.
    Returns monthly breakdown and total summary.
    """
    return service.get_monthly_cashflow(
        user_id=user_id, date_from=date_from, date_to=date_to, account_id=account_id
    )
