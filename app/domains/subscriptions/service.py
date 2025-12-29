from datetime import date, datetime, timedelta
import calendar
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.error_handlers import NotFoundError, ValidationError
from app.core.logging_config import get_logger
from app.domains.subscriptions.models import Subscription, BillingCycle
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
# Import TransactionUpdate for type checking if needed, but we'll use local import for Service

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

    def get_subscription_response(self, subscription_id: UUID, user_id: UUID) -> SubscriptionResponse:
        subscription = self.get_subscription(subscription_id, user_id)
        res = SubscriptionResponse.from_orm(subscription)
        res.is_paid_this_cycle = subscription.next_due_date > date.today()
        return res

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

        today = date.today()
        subscription_responses = []
        for s in subscriptions:
            res = SubscriptionResponse.from_orm(s)
            # Simple logic: if next_due_date is in the future, it's paid/upcoming
            # If it's today or in the past, it's due/overdue
            res.is_paid_this_cycle = s.next_due_date > today
            subscription_responses.append(res)

        meta = SubscriptionListMeta(
            total=total_count,
            page=filters.page,
            per_page=filters.per_page,
            has_next=has_next,
            has_previous=has_previous,
        )

        return SubscriptionListResponse(data=subscription_responses, meta=meta)

    def link_payment(self, subscription_id: UUID, transaction_id: UUID, user_id: UUID) -> Subscription:
        """
        Link a transaction to a subscription, updating the transaction and advancing the due date.
        """
        # Local import to avoid circular dependency
        from app.domains.transactions.service import TransactionService
        from app.domains.transactions.schemas import TransactionUpdate
        
        transaction_service = TransactionService(self.db)
        # 1. Get Subscription
        subscription = self.get_subscription(subscription_id, user_id)
        # 2. Verify Transaction ownership and existence
        transaction = transaction_service.get_account_transaction_by_id(transaction_id, user_id)
        # 3. Update Transaction (Link to sub, assign vendor)
        update_data = TransactionUpdate(
            subscription_id=subscription_id,
            vendor_id=subscription.vendor_id # Ensure vendor consistency
        )
        transaction_service.update_transaction(transaction_id, user_id, update_data)
        
        # 4. Advance Next Due Date
        if subscription.next_due_date:
            new_due_date = self._calculate_next_due_date(
                subscription.next_due_date, subscription.billing_cycle
            )
            subscription.next_due_date = new_due_date
            self.repository.update(subscription)
            
        return subscription

    def _calculate_next_due_date(self, current_date: date, cycle: BillingCycle) -> date:
        """Calculate the next due date based on the billing cycle."""
        if cycle == BillingCycle.WEEKLY:
            return current_date + timedelta(weeks=1)
        
        elif cycle == BillingCycle.MONTHLY:
            return self._add_months(current_date, 1)
            
        elif cycle == BillingCycle.QUARTERLY:
            return self._add_months(current_date, 3)
            
        elif cycle == BillingCycle.YEARLY:
            return self._add_months(current_date, 12)
            
        return current_date

    def _add_months(self, source_date: date, months: int) -> date:
        """
        Add months to a date, handling end-of-month overflow.
        
        Logic:
        1. Calculate the target year and month.
        2. Determine the number of days in that target month.
        3. Clamp the day: use the original day unless it exceeds the target month's length.
        """
        # 1. Calculate target year and month
        # (source_date.month + months - 1) // 12 calculates how many years to add
        new_year = source_date.year + (source_date.month + months - 1) // 12
        
        # (source_date.month + months - 1) % 12 + 1 calculates the new month (1-12)
        new_month = (source_date.month + months - 1) % 12 + 1
        
        # 2. Get the last valid day of that new month
        # monthrange returns (weekday_of_first_day, number_of_days_in_month)
        _, last_day_of_month = calendar.monthrange(new_year, new_month)
        
        # 3. Determine the new day
        # Keep original day unless it exceeds the month's length (e.g., Jan 31 -> Feb 28)
        new_day = min(source_date.day, last_day_of_month)
        
        return date(new_year, new_month, new_day)