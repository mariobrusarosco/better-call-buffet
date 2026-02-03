from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session
from app.core.error_handlers import NotFoundError
from app.domains.subscriptions.schemas import (
    LinkPaymentRequest,
    SubscriptionCreate,
    SubscriptionFilters,
    SubscriptionListResponse,
    SubscriptionResponse,
    SubscriptionUpdate,
    UpcomingPaymentsListResponse,
)
from app.domains.subscriptions.service import SubscriptionService

router = APIRouter()


@router.post("", response_model=SubscriptionResponse, status_code=201)
def create_subscription(
    subscription_in: SubscriptionCreate,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Create a new subscription."""
    service = SubscriptionService(db)
    try:
        subscription = service.create_subscription(subscription_in, current_user_id)
        return service.get_subscription_response(subscription.id, current_user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=SubscriptionListResponse)
def get_subscriptions(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    vendor_id: Optional[UUID] = Query(None, description="Filter by vendor"),
    category_id: Optional[UUID] = Query(None, description="Filter by category"),
    include_summary: bool = Query(False, description="Include financial dashboard summary in meta"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get all subscriptions for the current user."""
    service = SubscriptionService(db)
    filters = SubscriptionFilters(
        is_active=is_active,
        vendor_id=vendor_id,
        category_id=category_id,
        page=page,
        per_page=per_page,
    )
    return service.get_subscriptions(current_user_id, filters, include_summary)


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
def get_subscription(
    subscription_id: UUID,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get a specific subscription by ID."""
    service = SubscriptionService(db)
    try:
        return service.get_subscription_response(subscription_id, current_user_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{subscription_id}", response_model=SubscriptionResponse)
def update_subscription(
    subscription_id: UUID,
    subscription_update: SubscriptionUpdate,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Update a subscription."""
    service = SubscriptionService(db)
    try:
        service.update_subscription(subscription_id, subscription_update, current_user_id)
        return service.get_subscription_response(subscription_id, current_user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{subscription_id}", status_code=204)
def delete_subscription(
    subscription_id: UUID,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Delete a subscription."""
    service = SubscriptionService(db)
    try:
        service.delete_subscription(subscription_id, current_user_id)
        return None
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{subscription_id}/link-payment", response_model=SubscriptionResponse)
def link_payment(
    subscription_id: UUID,
    link_request: LinkPaymentRequest,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    service = SubscriptionService(db)
    try:
        service.link_payment(
            subscription_id=subscription_id,
            transaction_id=link_request.transaction_id,
            user_id=current_user_id
        )

        return service.get_subscription_response(subscription_id, current_user_id)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/upcoming-bills", response_model=UpcomingPaymentsListResponse)
def get_upcoming_bills(
    start_date: Optional[date] = Query(None, description="Start date for projection (defaults to today)"),
    end_date: Optional[date] = Query(None, description="End date for projection (defaults to 30 days from today)"),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """
    Project future subscription payments within a timeframe.
    Useful for cash flow forecasting and upcoming bill dashboards.
    """
    service = SubscriptionService(db)

    # Default to 30-day window
    if not start_date:
        start_date = date.today()

    if not end_date:
        end_date = start_date + timedelta(days=30)
    try:
        return service.get_upcoming_bills(current_user_id, start_date, end_date)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

