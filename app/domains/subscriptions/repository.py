from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, asc, or_
from sqlalchemy.orm import Session, joinedload

from app.domains.subscriptions.models import Subscription
from app.domains.subscriptions.schemas import SubscriptionFilters
from app.domains.tags.models import Tag


class SubscriptionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, subscription: Subscription) -> Subscription:
        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)
        return subscription

    def get_by_id(self, subscription_id: UUID, user_id: UUID) -> Optional[Subscription]:
        return (
            self.db.query(Subscription)
            .options(joinedload(Subscription.vendor), joinedload(Subscription.tags))
            .filter(
                and_(
                    Subscription.id == subscription_id, Subscription.user_id == user_id
                )
            )
            .first()
        )

    def update(self, subscription: Subscription) -> Subscription:
        self.db.commit()
        self.db.refresh(subscription)
        return subscription

    def delete(self, subscription: Subscription) -> None:
        self.db.delete(subscription)
        self.db.commit()

    def get_all_active_by_user(self, user_id: UUID) -> List[Subscription]:
        """Fetches all active subscriptions for a user, with relationships."""
        return (
            self.db.query(Subscription)
            .options(joinedload(Subscription.vendor), joinedload(Subscription.tags))
            .filter(
                and_(Subscription.user_id == user_id, Subscription.is_active == True)
            )
            .all()
        )

    def get_all_with_filters(
        self, user_id: UUID, filters: Optional[SubscriptionFilters] = None
    ) -> Tuple[List[Subscription], int]:
        # Base query with joined loads for performance
        query = (
            self.db.query(Subscription)
            .options(joinedload(Subscription.vendor), joinedload(Subscription.tags))
            .filter(Subscription.user_id == user_id)
        )

        # Apply structured filters
        if filters:
            query = self._apply_filters(query, filters)
            query = self._apply_sorting(query, filters)

            total_count = query.count()
            query = self._apply_pagination(query, filters)
        else:
            total_count = query.count()

        return query.all(), total_count

    def _apply_filters(self, query, filters: SubscriptionFilters):
        if filters.is_active is not None:
            query = query.filter(Subscription.is_active == filters.is_active)
        if filters.vendor_id:
            query = query.filter(Subscription.vendor_id == filters.vendor_id)
        if filters.tag_ids:
            predicates = [
                Subscription.tags.any(Tag.id == tag_id) for tag_id in filters.tag_ids
            ]
            if filters.tag_match == "any":
                query = query.filter(or_(*predicates))
            else:
                for predicate in predicates:
                    query = query.filter(predicate)
        return query

    def _apply_sorting(self, query, filters: SubscriptionFilters):
        # Default sort by next_due_date (upcoming first)
        query = query.order_by(asc(Subscription.next_due_date))
        return query

    def _apply_pagination(self, query, filters: SubscriptionFilters):
        page = max(1, filters.page)
        per_page = min(100, max(1, filters.per_page))

        offset = (page - 1) * per_page
        return query.offset(offset).limit(per_page)
