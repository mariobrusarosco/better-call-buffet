from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.error_handlers import NotFoundError, ValidationError
from app.core.logging_config import get_logger
from app.domains.subscriptions.models import Subscription
from app.domains.subscriptions.repository import SubscriptionRepository
from app.domains.subscriptions.schemas import (
    SubscriptionCreate,
    SubscriptionFilters,
    SubscriptionListMeta,
    SubscriptionListResponse,
    SubscriptionResponse,
    SubscriptionUpdate,
)
from app.domains.vendors.service import VendorService
from app.domains.categories.service import CategoryService

logger = get_logger(__name__)


class SubscriptionService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = SubscriptionRepository(db)
        self.vendor_service = VendorService(db)
        self.category_service = CategoryService(db)

    def create_subscription(
        self, subscription_data: SubscriptionCreate, user_id: UUID
    ) -> Subscription:
        # Validate Vendor
        if subscription_data.vendor_id:
            try:
                self.vendor_service.get_vendor(subscription_data.vendor_id, user_id)
            except NotFoundError:
                raise ValidationError(
                    message=f"Vendor with ID {subscription_data.vendor_id} not found.",
                    error_code="VENDOR_NOT_FOUND",
                )

        # Validate Category
        if subscription_data.category_id:
            category = self.category_service.repository.get_category_by_id(
                subscription_data.category_id, user_id
            )
            if not category:
                raise ValidationError(
                    message=f"Category with ID {subscription_data.category_id} not found.",
                    error_code="CATEGORY_NOT_FOUND",
                )

        subscription = Subscription(
            name=subscription_data.name,
            amount=subscription_data.amount,
            billing_cycle=subscription_data.billing_cycle,
            next_due_date=subscription_data.next_due_date,
            vendor_id=subscription_data.vendor_id,
            category_id=subscription_data.category_id,
            is_active=subscription_data.is_active,
            user_id=user_id,
        )
        return self.repository.create(subscription)

    def get_subscription(self, subscription_id: UUID, user_id: UUID) -> Subscription:
        subscription = self.repository.get_by_id(subscription_id, user_id)
        if not subscription:
            raise NotFoundError(
                message=f"Subscription with ID {subscription_id} not found",
                error_code="SUBSCRIPTION_NOT_FOUND",
            )
        return subscription

    def update_subscription(
        self, subscription_id: UUID, subscription_data: SubscriptionUpdate, user_id: UUID
    ) -> Subscription:
        subscription = self.get_subscription(subscription_id, user_id)

        # Validate Vendor if changing
        if subscription_data.vendor_id and subscription_data.vendor_id != subscription.vendor_id:
            try:
                self.vendor_service.get_vendor(subscription_data.vendor_id, user_id)
            except NotFoundError:
                raise ValidationError(
                    message=f"Vendor with ID {subscription_data.vendor_id} not found.",
                    error_code="VENDOR_NOT_FOUND",
                )

        # Validate Category if changing
        if subscription_data.category_id and subscription_data.category_id != subscription.category_id:
            category = self.category_service.repository.get_category_by_id(
                subscription_data.category_id, user_id
            )
            if not category:
                raise ValidationError(
                    message=f"Category with ID {subscription_data.category_id} not found.",
                    error_code="CATEGORY_NOT_FOUND",
                )

        update_data = subscription_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(subscription, key, value)

        return self.repository.update(subscription)

    def delete_subscription(self, subscription_id: UUID, user_id: UUID) -> None:
        subscription = self.get_subscription(subscription_id, user_id)
        # TODO: Add check for linked transactions when Phase 4 is implemented
        self.repository.delete(subscription)

    def get_subscriptions(
        self, user_id: UUID, filters: Optional[SubscriptionFilters] = None
    ) -> SubscriptionListResponse:
        if filters is None:
            filters = SubscriptionFilters()

        # Validate pagination
        filters.page = max(1, filters.page)
        filters.per_page = min(100, max(1, filters.per_page))

        subscriptions, total_count = self.repository.get_all_with_filters(user_id, filters)

        # Calculate pagination metadata
        total_pages = (total_count + filters.per_page - 1) // filters.per_page
        has_next = filters.page < total_pages
        has_previous = filters.page > 1

        subscription_responses = [SubscriptionResponse.from_orm(s) for s in subscriptions]

        meta = SubscriptionListMeta(
            total=total_count,
            page=filters.page,
            per_page=filters.per_page,
            has_next=has_next,
            has_previous=has_previous,
        )

        return SubscriptionListResponse(data=subscription_responses, meta=meta)
