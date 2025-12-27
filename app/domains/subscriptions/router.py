from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session
from app.domains.subscriptions.schemas import (
    SubscriptionCreate,
    SubscriptionFilters,
    SubscriptionListResponse,
    SubscriptionResponse,
    SubscriptionUpdate,
)
from app.domains.subscriptions.service import SubscriptionService

router = APIRouter()


@router.post("", response_model=SubscriptionResponse, status_code=201)
def create_subscription(
    subscription_in: SubscriptionCreate,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    service = SubscriptionService(db)
    try:
        return service.create_subscription(subscription_in, current_user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Failed to create subscription")


@router.get("", response_model=SubscriptionListResponse)
def get_subscriptions(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    vendor_id: Optional[UUID] = Query(None, description="Filter by vendor"),
    category_id: Optional[UUID] = Query(None, description="Filter by category"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    service = SubscriptionService(db)
    filters = SubscriptionFilters(
        is_active=is_active,
        vendor_id=vendor_id,
        category_id=category_id,
        page=page,
        per_page=per_page,
    )
    return service.get_subscriptions(current_user_id, filters)


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
def get_subscription(
    subscription_id: UUID,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    service = SubscriptionService(db)
    try:
        return service.get_subscription(subscription_id, current_user_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail="Subscription not found")


@router.patch("/{subscription_id}", response_model=SubscriptionResponse)
def update_subscription(
    subscription_id: UUID,
    subscription_update: SubscriptionUpdate,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    service = SubscriptionService(db)
    try:
        return service.update_subscription(
            subscription_id, subscription_update, current_user_id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail="Failed to update subscription")


@router.delete("/{subscription_id}", status_code=204)
def delete_subscription(
    subscription_id: UUID,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    service = SubscriptionService(db)
    try:
        service.delete_subscription(subscription_id, current_user_id)
        return None
    except Exception as e:
        raise HTTPException(status_code=404, detail="Subscription not found")
