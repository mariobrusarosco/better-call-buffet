from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.core.error_handlers import ValidationError
from app.domains.subscriptions.schemas import (
    SubscriptionCreate,
    SubscriptionFilters,
    SubscriptionUpdate,
)
from app.domains.subscriptions.service import SubscriptionService
from app.domains.tags.models import Tag


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


def build_tag(user_id):
    now = datetime.utcnow()
    return SimpleNamespace(
        id=uuid4(),
        user_id=user_id,
        name="Streaming",
        display_order=0,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def build_service():
    service = SubscriptionService(MagicMock())
    service.repository = MagicMock()
    service.repository.create.side_effect = lambda subscription: subscription
    service.repository.update.side_effect = lambda subscription: subscription
    service.tag_service = MagicMock()
    return service


def build_create_payload(**overrides):
    payload = {
        "name": "Netflix Family",
        "amount": 55.90,
        "billing_cycle": "monthly",
        "next_due_date": date.today() + timedelta(days=10),
    }
    payload.update(overrides)
    return SubscriptionCreate(**payload)


def test_create_subscription_assigns_validated_tags():
    service = build_service()
    user_id = uuid4()
    tags = [Tag(id=uuid4(), name="Streaming"), Tag(id=uuid4(), name="Family")]
    tag_ids = [tag.id for tag in tags]
    service.tag_service.validate_tag_assignment.return_value = tags

    subscription = service.create_subscription(
        build_create_payload(tag_ids=tag_ids), user_id
    )

    service.tag_service.validate_tag_assignment.assert_called_once_with(
        tag_ids, user_id
    )
    assert subscription.tags == tags
    service.repository.create.assert_called_once_with(subscription)


def test_create_subscription_without_tags_validates_an_empty_list():
    service = build_service()
    user_id = uuid4()
    service.tag_service.validate_tag_assignment.return_value = []

    subscription = service.create_subscription(build_create_payload(), user_id)

    service.tag_service.validate_tag_assignment.assert_called_once_with([], user_id)
    assert subscription.tags == []


def test_create_subscription_rejects_invalid_tags_without_persisting():
    service = build_service()
    service.tag_service.validate_tag_assignment.side_effect = ValidationError(
        message="One or more tags do not exist, are inactive, or are not owned by the user",
        error_code="INVALID_TAG_ASSIGNMENT",
    )

    with pytest.raises(ValidationError) as error:
        service.create_subscription(build_create_payload(tag_ids=[uuid4()]), uuid4())

    assert error.value.error_code == "INVALID_TAG_ASSIGNMENT"
    service.repository.create.assert_not_called()


def test_create_payload_rejects_duplicate_tag_ids():
    tag_id = uuid4()

    with pytest.raises(PydanticValidationError):
        build_create_payload(tag_ids=[tag_id, tag_id])


def test_update_subscription_replaces_tags():
    service = build_service()
    user_id = uuid4()
    subscription = build_subscription(date.today())
    subscription.tags = [build_tag(user_id)]
    service.repository.get_by_id.return_value = subscription
    new_tags = [build_tag(user_id)]
    service.tag_service.validate_tag_assignment.return_value = new_tags

    result = service.update_subscription(
        subscription.id, SubscriptionUpdate(tag_ids=[new_tags[0].id]), user_id
    )

    service.tag_service.validate_tag_assignment.assert_called_once_with(
        [new_tags[0].id], user_id
    )
    assert result.tags == new_tags


def test_update_subscription_with_null_tag_ids_clears_tags():
    service = build_service()
    user_id = uuid4()
    subscription = build_subscription(date.today())
    subscription.tags = [build_tag(user_id)]
    service.repository.get_by_id.return_value = subscription
    service.tag_service.validate_tag_assignment.return_value = []

    result = service.update_subscription(
        subscription.id, SubscriptionUpdate(tag_ids=None), user_id
    )

    service.tag_service.validate_tag_assignment.assert_called_once_with([], user_id)
    assert result.tags == []


def test_update_subscription_without_tag_ids_keeps_existing_tags():
    service = build_service()
    user_id = uuid4()
    subscription = build_subscription(date.today())
    existing_tags = [build_tag(user_id)]
    subscription.tags = existing_tags
    service.repository.get_by_id.return_value = subscription

    result = service.update_subscription(
        subscription.id, SubscriptionUpdate(name="Renamed"), user_id
    )

    service.tag_service.validate_tag_assignment.assert_not_called()
    assert result.tags == existing_tags
    assert result.name == "Renamed"


def test_subscription_response_exposes_tags_and_tag_ids():
    service = build_service()
    user_id = uuid4()
    subscription = build_subscription(date.today() + timedelta(days=1))
    tags = [build_tag(user_id), build_tag(user_id)]
    subscription.tags = tags
    service.repository.get_by_id.return_value = subscription

    response = service.get_subscription_response(subscription.id, user_id)

    assert response.tag_ids == [tag.id for tag in tags]
    assert [tag.id for tag in response.tags] == [tag.id for tag in tags]
