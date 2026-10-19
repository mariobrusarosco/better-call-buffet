from datetime import date
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session
from app.domains.investments.schemas import (
    InvestmentBalanceListResponse,
    InvestmentListResponse,
)
from app.domains.investments.service import InvestmentService

router = APIRouter()


def get_investment_service(db: Session = Depends(get_db_session)) -> InvestmentService:
    return InvestmentService(db)


@router.get("", response_model=InvestmentListResponse)
def list_investments(
    user_id: UUID = Depends(get_current_user_id),
    service: InvestmentService = Depends(get_investment_service),
):
    """Every active investment account with its current balance, how much went
    into it and how much it grew, plus the totals."""
    return service.list_investments(user_id)


@router.get("/balances", response_model=InvestmentBalanceListResponse)
def list_investment_balances(
    investment_id: Optional[UUID] = Query(None, description="Only this investment"),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: Literal["date", "balance", "created_at"] = Query("date"),
    sort_order: Literal["asc", "desc"] = Query("desc"),
    user_id: UUID = Depends(get_current_user_id),
    service: InvestmentService = Depends(get_investment_service),
):
    """Every saved balance with the movement, diff and % since the previous
    one (the spreadsheet's DATE, MOV, BALANCE, DIFF, % columns)."""
    return service.list_balances(
        user_id, investment_id, date_from, date_to, sort_by, sort_order, page, per_page
    )
