from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from app.domains.subscriptions.schemas import SubscriptionFilters
from app.domains.subscriptions.service import SubscriptionService


def build_subscription(next_due_date):
    now = datetime.utcnow()
    return SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        name="Health plan",
        amount=100.0,
        billing_cycle="monthly",
        next_due_date=next_due_date,
        vendor_id=None,
        is_active=True,
        created_at=now,
        updated_at=now,
        vendor=None,
        tags=[],
    )


def test_list_subscriptions_computes_response_only_paid_status():
    service = SubscriptionService(MagicMock())
    service.repository = MagicMock()
    subscription = build_subscription(date.today() + timedelta(days=1))
    service.repository.get_all_with_filters.return_value = ([subscription], 1)

    result = service.get_subscriptions(
        subscription.user_id,
        SubscriptionFilters(is_active=True),
    )

    assert result.data[0].is_paid_this_cycle is True
    assert result.data[0].tag_ids == []
    assert result.data[0].tags == []


def test_list_subscriptions_marks_due_subscription_unpaid():
    service = SubscriptionService(MagicMock())
    service.repository = MagicMock()
    subscription = build_subscription(date.today())
    service.repository.get_all_with_filters.return_value = ([subscription], 1)

    result = service.get_subscriptions(subscription.user_id)

    assert result.data[0].is_paid_this_cycle is False
