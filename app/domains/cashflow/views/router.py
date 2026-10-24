from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session
from app.domains.cashflow.views.schemas import (
    CashflowTransactionListResponse,
    CashflowViewCreate,
    CashflowViewOverlapItem,
    CashflowViewResponse,
    CashflowViewSummaryResponse,
    CashflowViewUpdate,
)
from app.domains.cashflow.views.service import CashflowViewService
from app.domains.transactions.constants import MovementType

# Mounted under /cashflow/views.
router = APIRouter()


def get_view_service(db: Session = Depends(get_db_session)) -> CashflowViewService:
    return CashflowViewService(db)


# ---- CRUD -------------------------------------------------------------------------


@router.get("", response_model=List[CashflowViewResponse])
def list_views(
    user_id: UUID = Depends(get_current_user_id),
    service: CashflowViewService = Depends(get_view_service),
):
    return service.list_views(user_id)


@router.post(
    "", response_model=CashflowViewResponse, status_code=status.HTTP_201_CREATED
)
def create_view(
    data: CashflowViewCreate,
    user_id: UUID = Depends(get_current_user_id),
    service: CashflowViewService = Depends(get_view_service),
):
    return service.create_view(data, user_id)


@router.patch("/{view_id}", response_model=CashflowViewResponse)
def update_view(
    view_id: UUID,
    data: CashflowViewUpdate,
    user_id: UUID = Depends(get_current_user_id),
    service: CashflowViewService = Depends(get_view_service),
):
    """Omitted fields stay unchanged. `groups`, when sent, replaces the whole
    list (array order = display order) and the groups get new ids."""
    return service.update_view(view_id, data, user_id)


@router.delete("/{view_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_view(
    view_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: CashflowViewService = Depends(get_view_service),
):
    service.delete_view(view_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---- Reporting --------------------------------------------------------------------
# All take the same filters: date_from/date_to (optional, inclusive whole days)
# and movement_type (default expense).


@router.get("/{view_id}/summary", response_model=CashflowViewSummaryResponse)
def get_summary(
    view_id: UUID,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    movement_type: MovementType = Query(MovementType.EXPENSE),
    user_id: UUID = Depends(get_current_user_id),
    service: CashflowViewService = Depends(get_view_service),
):
    """Total and count per group, plus the ungrouped remainder, over ALL
    matching transactions (not paginated). Groups can share transactions;
    never add group totals up."""
    return service.get_summary(view_id, user_id, date_from, date_to, movement_type)


@router.get("/{view_id}/overlaps", response_model=List[CashflowViewOverlapItem])
def get_overlaps(
    view_id: UUID,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    movement_type: MovementType = Query(MovementType.EXPENSE),
    user_id: UUID = Depends(get_current_user_id),
    service: CashflowViewService = Depends(get_view_service),
):
    """Transactions that fall into two or more groups of the view."""
    return service.get_overlaps(view_id, user_id, date_from, date_to, movement_type)


@router.get(
    "/{view_id}/groups/{group_id}/transactions",
    response_model=CashflowTransactionListResponse,
)
def list_group_transactions(
    view_id: UUID,
    group_id: UUID,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    movement_type: MovementType = Query(MovementType.EXPENSE),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    user_id: UUID = Depends(get_current_user_id),
    service: CashflowViewService = Depends(get_view_service),
):
    """The transactions behind a group's summary total, newest first. Takes
    sub-group and parent ids; a parent lists what its sub-groups match, each
    once. meta.total equals the group's count in /summary."""
    return service.list_group_transactions(
        view_id, group_id, user_id, date_from, date_to, movement_type, page, per_page
    )


@router.get(
    "/{view_id}/ungrouped/transactions",
    response_model=CashflowTransactionListResponse,
)
def list_ungrouped_transactions(
    view_id: UUID,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    movement_type: MovementType = Query(MovementType.EXPENSE),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    user_id: UUID = Depends(get_current_user_id),
    service: CashflowViewService = Depends(get_view_service),
):
    """Transactions that match none of the view's groups, newest first.
    meta.total equals ungrouped.count in /summary."""
    return service.list_ungrouped_transactions(
        view_id, user_id, date_from, date_to, movement_type, page, per_page
    )
