from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.core.error_handlers import NotFoundError, ValidationError
from app.domains.installments.schemas import (
    InstallmentPlanCreate,
    InstallmentPlanUpdate,
)
from app.domains.installments.service import InstallmentService


def build_service(plan):
    service = InstallmentService(MagicMock())
    service.repository = MagicMock()
    service.repository.get_plan_by_id.return_value = plan
    service.vendor_service = MagicMock()
    service.tag_service = MagicMock()
    service.credit_card_service = MagicMock()
    return service


def build_plan():
    return SimpleNamespace(
        id=uuid4(),
        name="Clothes",
        description=None,
        total_amount=3231.70,
        vendor_id=None,
        credit_card_id=None,
        tags=[SimpleNamespace(id=uuid4())],
    )


def test_update_plan_renames_and_keeps_everything_else():
    plan = build_plan()
    service = build_service(plan)
    original_tags = plan.tags

    result = service.update_plan(
        plan.id, InstallmentPlanUpdate(name="  Winter clothes "), uuid4()
    )

    assert result.name == "Winter clothes"
    assert result.tags is original_tags
    assert result.total_amount == 3231.70
    service.repository.update_plan.assert_called_once_with(plan)
    service.tag_service.validate_tag_assignment.assert_not_called()


def test_update_plan_with_null_tag_ids_clears_tags():
    plan = build_plan()
    service = build_service(plan)
    service.tag_service.validate_tag_assignment.return_value = []
    user_id = uuid4()

    result = service.update_plan(plan.id, InstallmentPlanUpdate(tag_ids=None), user_id)

    service.tag_service.validate_tag_assignment.assert_called_once_with([], user_id)
    assert result.tags == []


def test_update_plan_rejects_a_credit_card_the_user_does_not_own():
    plan = build_plan()
    service = build_service(plan)
    service.credit_card_service.get_user_unique_credit_card_with_filters.return_value = (
        None
    )

    with pytest.raises(ValidationError) as error:
        service.update_plan(
            plan.id, InstallmentPlanUpdate(credit_card_id=uuid4()), uuid4()
        )

    assert error.value.error_code == "CREDIT_CARD_NOT_FOUND"
    service.repository.update_plan.assert_not_called()


def test_update_plan_rejects_an_unknown_vendor():
    plan = build_plan()
    service = build_service(plan)
    service.vendor_service.get_vendor.side_effect = NotFoundError(
        message="Vendor not found", error_code="VENDOR_NOT_FOUND"
    )

    with pytest.raises(ValidationError) as error:
        service.update_plan(plan.id, InstallmentPlanUpdate(vendor_id=uuid4()), uuid4())

    assert error.value.error_code == "VENDOR_NOT_FOUND"
    service.repository.update_plan.assert_not_called()


@pytest.mark.parametrize(
    "payload",
    [{"name": "   "}, {"name": None}, {"status": None}],
    ids=["blank-name", "null-name", "null-status"],
)
def test_update_payload_rejects_invalid_values(payload):
    with pytest.raises(PydanticValidationError):
        InstallmentPlanUpdate(**payload)


def test_update_payload_ignores_schedule_fields():
    update = InstallmentPlanUpdate(total_amount=1, installment_count=3)

    assert update.model_dump(exclude_unset=True) == {}


def test_create_plan_rejects_a_credit_card_the_user_does_not_own():
    service = build_service(None)
    service.credit_card_service.get_user_unique_credit_card_with_filters.return_value = (
        None
    )
    service.tag_service.validate_tag_assignment.return_value = []
    plan_data = InstallmentPlanCreate(
        name="Clothes",
        total_amount=3231.70,
        installment_count=10,
        start_date="2026-09-20",
        credit_card_id=uuid4(),
    )

    with pytest.raises(ValidationError) as error:
        service.create_plan(plan_data, uuid4())

    assert error.value.error_code == "CREDIT_CARD_NOT_FOUND"
    service.repository.create_plan.assert_not_called()
