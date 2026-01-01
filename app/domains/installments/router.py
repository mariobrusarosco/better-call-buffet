from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session
from app.domains.installments.schemas import (
    InstallmentFilters,
    InstallmentPlanCreate,
    InstallmentPlanListResponse,
    InstallmentPlanResponse,
    InstallmentPlanUpdate,
    InstallmentUpdate,
    LinkInstallmentRequest,
    InstallmentResponse
)
from app.domains.installments.service import InstallmentService

router = APIRouter()


@router.post("/plans", response_model=InstallmentPlanResponse, status_code=201)
def create_installment_plan(
    plan_in: InstallmentPlanCreate,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Create a new installment plan and generate its installments."""
    service = InstallmentService(db)
    try:
        return service.create_plan(plan_in, current_user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/plans", response_model=InstallmentPlanListResponse)
def list_installment_plans(
    status: Optional[str] = Query(None),
    vendor_id: Optional[UUID] = Query(None),
    category_id: Optional[UUID] = Query(None),
    credit_card_id: Optional[UUID] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """List all installment plans for the user with filters."""
    service = InstallmentService(db)
    filters = InstallmentFilters(
        status=status,
        vendor_id=vendor_id,
        category_id=category_id,
        credit_card_id=credit_card_id,
        page=page,
        per_page=per_page
    )
    return service.list_plans(current_user_id, filters)


@router.get("/plans/{plan_id}", response_model=InstallmentPlanResponse)
def get_installment_plan(
    plan_id: UUID,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get a specific installment plan with all its monthly installments."""
    service = InstallmentService(db)
    try:
        return service.get_plan(plan_id, current_user_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/plans/{plan_id}", status_code=204)
def delete_installment_plan(
    plan_id: UUID,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Delete an installment plan and all its projected installments."""
    service = InstallmentService(db)
    try:
        service.delete_plan(plan_id, current_user_id)
        return None
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{installment_id}", response_model=InstallmentResponse)
def update_installment(
    installment_id: UUID,
    update_in: InstallmentUpdate,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Update a specific installment's data (e.g. adjust amount or due date)."""
    service = InstallmentService(db)
    try:
        return service.update_installment(installment_id, update_in, current_user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{installment_id}/link-transaction", response_model=InstallmentResponse)
def link_installment_to_transaction(
    installment_id: UUID,
    link_request: LinkInstallmentRequest,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """
    Link a real transaction to a projected installment.
    This marks the installment as LINKED and updates the transaction.
    """
    service = InstallmentService(db)
    try:
        return service.link_transaction(
            installment_id=installment_id,
            transaction_id=link_request.transaction_id,
            user_id=current_user_id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
