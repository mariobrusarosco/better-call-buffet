from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session
from app.domains.cashflow.schemas import (
    CashflowSummary,
    CashflowViewCreate,
    CashflowViewGroupTransactionListResponse,
    CashflowViewOverlapItem,
    CashflowViewResponse,
    CashflowViewSummaryResponse,
    CashflowViewUpdate,
)
from app.domains.cashflow.service import CashflowService
from app.domains.transactions.constants import MovementType

router = APIRouter()


def get_cashflow_service(db: Session = Depends(get_db_session)) -> CashflowService:
    return CashflowService(db)


# ---- Monthly cashflow -------------------------------------------------------


@router.get("", response_model=CashflowSummary)
def get_cashflow_analytics(
    date_from: date,
    date_to: date,
    account_id: Optional[UUID] = None,
    user_id: UUID = Depends(get_current_user_id),
    service: CashflowService = Depends(get_cashflow_service),
):
    """
    Get aggregated cashflow data (income, expenses, savings, investments) for a specific date range.
    Returns monthly breakdown and total summary.
    """
    return service.get_cashflow_analytics(
        user_id=user_id, date_from=date_from, date_to=date_to, account_id=account_id
    )


# Deprecated: the original path, kept until the frontend calls /cashflow.
legacy_router = APIRouter()
legacy_router.add_api_route(
    "/analytics/cashflow",
    get_cashflow_analytics,
    methods=["GET"],
    response_model=CashflowSummary,
    deprecated=True,
    tags=["cashflow"],
)


# ---- Views ------------------------------------------------------------------


@router.get("/views", response_model=List[CashflowViewResponse])
def list_cashflow_views(
    user_id: UUID = Depends(get_current_user_id),
    service: CashflowService = Depends(get_cashflow_service),
):
    return service.list_views(user_id)


@router.post(
    "/views",
    response_model=CashflowViewResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_cashflow_view(
    data: CashflowViewCreate,
    user_id: UUID = Depends(get_current_user_id),
    service: CashflowService = Depends(get_cashflow_service),
):
    return service.create_view(data, user_id)


@router.patch("/views/{view_id}", response_model=CashflowViewResponse)
def update_cashflow_view(
    view_id: UUID,
    data: CashflowViewUpdate,
    user_id: UUID = Depends(get_current_user_id),
    service: CashflowService = Depends(get_cashflow_service),
):
    """Omitted fields stay unchanged. `groups`, when sent, replaces the whole
    list (array order = display order) and the groups get new ids."""
    return service.update_view(view_id, data, user_id)


@router.delete("/views/{view_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cashflow_view(
    view_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: CashflowService = Depends(get_cashflow_service),
):
    service.delete_view(view_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/views/{view_id}/summary", response_model=CashflowViewSummaryResponse)
def get_cashflow_view_summary(
    view_id: UUID,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    movement_type: MovementType = Query(MovementType.EXPENSE),
    user_id: UUID = Depends(get_current_user_id),
    service: CashflowService = Depends(get_cashflow_service),
):
    """Totals per group and per tag over ALL matching transactions (not
    paginated). Groups can share transactions; never add group totals up."""
    return service.get_view_summary(view_id, user_id, date_from, date_to, movement_type)


@router.get("/views/{view_id}/overlaps", response_model=List[CashflowViewOverlapItem])
def get_cashflow_view_overlaps(
    view_id: UUID,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    movement_type: MovementType = Query(MovementType.EXPENSE),
    user_id: UUID = Depends(get_current_user_id),
    service: CashflowService = Depends(get_cashflow_service),
):
    """Transactions that fall into two or more groups of the view."""
    return service.get_view_overlaps(
        view_id, user_id, date_from, date_to, movement_type
    )


@router.get(
    "/views/{view_id}/groups/{group_id}/transactions",
    response_model=CashflowViewGroupTransactionListResponse,
)
def list_cashflow_view_group_transactions(
    view_id: UUID,
    group_id: UUID,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    movement_type: MovementType = Query(MovementType.EXPENSE),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    user_id: UUID = Depends(get_current_user_id),
    service: CashflowService = Depends(get_cashflow_service),
):
    """The transactions behind a group's summary total, newest first. Same
    match and filters as /summary, so meta.total equals the group's count."""
    return service.list_group_transactions(
        view_id,
        group_id,
        user_id,
        date_from,
        date_to,
        movement_type,
        page,
        per_page,
    )


@router.get(
    "/views/{view_id}/ungrouped/transactions",
    response_model=CashflowViewGroupTransactionListResponse,
)
def list_cashflow_view_ungrouped_transactions(
    view_id: UUID,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    movement_type: MovementType = Query(MovementType.EXPENSE),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    user_id: UUID = Depends(get_current_user_id),
    service: CashflowService = Depends(get_cashflow_service),
):
    """Transactions that match none of the view's groups, newest first.
    meta.total equals the summary's ungrouped.count."""
    return service.list_ungrouped_transactions(
        view_id,
        user_id,
        date_from,
        date_to,
        movement_type,
        page,
        per_page,
    )
