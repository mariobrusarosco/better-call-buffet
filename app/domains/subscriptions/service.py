from datetime import date, datetime, timedelta
from app.core.utils.date import add_months
from uuid import UUID
from typing import Optional, List, Dict
from app.core.logging_config import get_logger
from app.core.error_handlers import NotFoundError, ValidationError
from app.domains.subscriptions.models import Subscription, BillingCycle
from app.domains.subscriptions.repository import SubscriptionRepository
from app.domains.subscriptions.schemas import (
    CategoryBreakdownItem,
    MonthlyForecastItem,
    SubscriptionCreate,
    SubscriptionFilters,
    SubscriptionListMeta,
    SubscriptionListResponse,
    SubscriptionResponse,
    SubscriptionSummary,
    SubscriptionUpdate,
    UpcomingPaymentResponse,
    UpcomingPaymentsListResponse,
)
from app.domains.vendors.service import VendorService
from app.domains.categories.service import CategoryService
# Import TransactionUpdate for type checking if needed, but we'll use local import for Service
from sqlalchemy.orm import Session

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
        self, 
        user_id: UUID, 
        filters: Optional[SubscriptionFilters] = None,
        include_summary: bool = False
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

        summary = None
        if include_summary:
            summary = self._calculate_summary(user_id)

        meta = SubscriptionListMeta(
            total=total_count,
            page=filters.page,
            per_page=filters.per_page,
            has_next=has_next,
            has_previous=has_previous,
            summary=summary,
        )

        return SubscriptionListResponse(data=subscription_responses, meta=meta)

    def get_upcoming_bills(
        self, user_id: UUID, start_date: date, end_date: date
    ) -> UpcomingPaymentsListResponse:
        """Projects all upcoming subscription payments within a given timeframe."""
        projected_payments = []
        
        # 1. Fetch all active subscriptions
        active_subscriptions = self.repository.get_all_active_by_user(user_id)

        for sub in active_subscriptions:
            is_subscripiton_in_date_range = sub.next_due_date >= start_date and sub.next_due_date <= end_date
            if not is_subscripiton_in_date_range:
                continue

            projected_payments.append(
                UpcomingPaymentResponse(
                    id=sub.id,
                    name=sub.name,
                    vendor=sub.vendor,
                    amount=float(sub.amount),
                    due_date=sub.next_due_date,
                    source_type="subscription"
                )
            )
  
        return UpcomingPaymentsListResponse(
            data=projected_payments,
            total=len(projected_payments)
        )

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
        # 3. Update Transaction (Link to sub, assign vendor, mark as paid)
        update_data = TransactionUpdate(
            subscription_id=subscription_id,
            vendor_id=subscription.vendor_id, # Ensure vendor consistency
            is_paid=True # Auto-mark as paid upon linking
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
        if cycle == BillingCycle.weekly:
            return current_date + timedelta(weeks=1)
        
        elif cycle == BillingCycle.monthly:
            return add_months(current_date, 1)
            
        elif cycle == BillingCycle.quarterly:
            return add_months(current_date, 3)
            
        elif cycle == BillingCycle.yearly:
            return add_months(current_date, 12)
            
        return current_date

    def _normalize_to_monthly(self, amount: float, cycle: BillingCycle) -> float:
        """Normalize subscription amount to a monthly burn rate."""
        if cycle == BillingCycle.weekly:
            # 52 weeks / 12 months = 4.333...
            return float(amount) * 52 / 12
        elif cycle == BillingCycle.monthly:
            return float(amount)
        elif cycle == BillingCycle.quarterly:
            return float(amount) / 3
        elif cycle == BillingCycle.yearly:
            return float(amount) / 12
        return float(amount)

    ## [TODO] Review this logic
    def _calculate_forecast(self, active_subscriptions: List[Subscription]) -> List[MonthlyForecastItem]:
        """Project expenses for the next 12 months based on billing cycles."""
        today = date.today()
        forecast_map: Dict[str, float] = {}
        
        # Initialize buckets for next 12 months (key: "Jan 26")
        # We start from current month or next month? 
        # Requirement says "monthly_forecast: An array of the next 12 months"
        # Let's include current month + 11 future months
        for i in range(12):
            future_date = add_months(today, i)
            key = future_date.strftime("%b %y")
            forecast_map[key] = 0.0

        end_date = add_months(today, 12)

        for sub in active_subscriptions:
            # Simulate payments for one year
            current_date = sub.next_due_date
            
            # If next due date is already passed (overdue) but not updated, 
            # we should start projecting from "future" or handle overdue as immediate?
            # For forecast, let's assume we project from the next VALID due date.
            # But here we rely on stored next_due_date.
            
            # Loop while the simulated date is within our 1-year window
            while current_date < end_date:
                # We only sum if it falls in our window. 
                # (next_due_date could be way in future, e.g. yearly sub)
                if current_date >= today: # Only count future/today payments
                    key = current_date.strftime("%b %y")
                    # Only add if key exists in our 12-month window
                    if key in forecast_map:
                        forecast_map[key] += float(sub.amount)
                
                # Advance date
                current_date = self._calculate_next_due_date(current_date, sub.billing_cycle)

        return [
            MonthlyForecastItem(month=k, amount=round(v, 2)) 
            for k, v in forecast_map.items()
        ]

    ## [TODO] Review this logic
    def _calculate_summary(self, user_id: UUID) -> SubscriptionSummary:
        """Calculate dashboard metrics for subscriptions."""
        active_subs = self.repository.get_all_active_by_user(user_id)
        
        monthly_burn_rate = 0.0
        category_map: Dict[str, float] = {}
        
        for sub in active_subs:
            normalized_amount = self._normalize_to_monthly(sub.amount, sub.billing_cycle)
            monthly_burn_rate += normalized_amount
            
            # Category breakdown (using normalized amounts)
            cat_name = sub.category.name if sub.category else "Uncategorized"
            category_map[cat_name] = category_map.get(cat_name, 0.0) + normalized_amount
            
        yearly_projection = monthly_burn_rate * 12
        
        # Calculate due next 30 days (Cashflow, not normalized)
        today = date.today()
        next_30 = today + timedelta(days=30)
        due_next_30 = 0.0
        
        for sub in active_subs:
             current_date = sub.next_due_date
             # Simulate simply for the next 30 days
             # Careful: infinite loop if cycle is 0 days (impossible by enum)
             temp_date = current_date
             while temp_date <= next_30:
                 if temp_date >= today:
                     due_next_30 += float(sub.amount)
                 temp_date = self._calculate_next_due_date(temp_date, sub.billing_cycle)

        category_breakdown = [
            CategoryBreakdownItem(name=k, amount=round(v, 2)) 
            for k, v in category_map.items()
        ]
        
        monthly_forecast = self._calculate_forecast(active_subs)
        
        return SubscriptionSummary(
            monthly_burn_rate=round(monthly_burn_rate, 2),
            yearly_projection=round(yearly_projection, 2),
            due_next_30_days=round(due_next_30, 2),
            active_count=len(active_subs),
            category_breakdown=category_breakdown,
            monthly_forecast=monthly_forecast
        )