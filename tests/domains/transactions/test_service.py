from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core.error_handlers import ValidationError
from app.domains.transactions.schemas import TransactionBulkUpdate
from app.domains.transactions.service import TransactionService


def build_service():
    db = MagicMock()
    service = TransactionService(db)
    service.repository = MagicMock()
    return service, db


def build_tag(tag_id, user_id):
    now = datetime.utcnow()
    return SimpleNamespace(
        id=tag_id,
        user_id=user_id,
        name="Health",
        dimension_id=None,
        display_order=0,
        is_active=True,
        created_at=now,
        updated_at=now,
        dimension=None,
    )


def build_transaction_response_data(transaction_id, user_id, tags):
    now = datetime.utcnow()
    return {
        "id": transaction_id,
        "user_id": user_id,
        "account_id": uuid4(),
        "credit_card_id": None,
        "from_account_id": None,
        "to_account_id": None,
        "broker_id": uuid4(),
        "is_paid": True,
        "date": now,
        "amount": 25.0,
        "description": "Lunch",
        "movement_type": "expense",
        "tag_ids": [tag.id for tag in tags],
        "tags": tags,
        "ignored": False,
        "vendor_id": None,
        "subscription_id": None,
        "installment_id": None,
        "is_deleted": False,
        "created_at": now,
        "updated_at": now,
    }


def test_bulk_update_commits_once_after_response_is_validated():
    service, db = build_service()
    user_id = uuid4()
    transaction_ids = [uuid4(), uuid4()]
    tag_id = uuid4()
    tag = build_tag(tag_id, user_id)
    request = TransactionBulkUpdate(
        transaction_ids=transaction_ids,
        changes={"tag_ids": [tag_id]},
    )
    locked_transactions = [
        SimpleNamespace(id=transaction_id) for transaction_id in transaction_ids
    ]
    service.repository.get_by_ids_for_update.return_value = locked_transactions
    service.repository.bulk_update_transactions.return_value = [
        build_transaction_response_data(transaction_id, user_id, [tag])
        for transaction_id in transaction_ids
    ]
    service.tag_service.validate_tag_assignment = MagicMock(return_value=[tag])

    response = service.update_transactions_bulk(request, user_id)

    assert response.updated_count == 2
    assert [transaction.id for transaction in response.transactions] == transaction_ids
    service.repository.bulk_update_transactions.assert_called_once_with(
        locked_transactions,
        user_id,
        {"tags": [tag]},
    )
    db.commit.assert_called_once_with()
    db.rollback.assert_not_called()


def test_bulk_update_rolls_back_when_any_transaction_is_missing():
    service, db = build_service()
    request = TransactionBulkUpdate(
        transaction_ids=[uuid4(), uuid4()],
        changes={"tag_ids": [uuid4()]},
    )
    service.repository.get_by_ids_for_update.return_value = [SimpleNamespace()]

    with pytest.raises(HTTPException) as error:
        service.update_transactions_bulk(request, uuid4())

    assert error.value.status_code == 404
    service.repository.bulk_update_transactions.assert_not_called()
    db.rollback.assert_called_once_with()


def test_bulk_update_rejects_tag_not_owned_by_user():
    service, db = build_service()
    transaction_id = uuid4()
    request = TransactionBulkUpdate(
        transaction_ids=[transaction_id],
        changes={"tag_ids": [uuid4()]},
    )
    service.repository.get_by_ids_for_update.return_value = [
        SimpleNamespace(id=transaction_id)
    ]
    service.tag_service.validate_tag_assignment = MagicMock(
        side_effect=ValidationError(
            message="One or more tags are invalid",
            error_code="INVALID_TAG_ASSIGNMENT",
        )
    )

    with pytest.raises(ValidationError) as error:
        service.update_transactions_bulk(request, uuid4())

    assert error.value.status_code == 422
    assert error.value.error_code == "INVALID_TAG_ASSIGNMENT"
    service.repository.bulk_update_transactions.assert_not_called()
    db.rollback.assert_called_once_with()


def test_bulk_update_validates_every_resulting_transaction_target():
    service, db = build_service()
    first_id = uuid4()
    second_id = uuid4()
    credit_card_id = uuid4()
    request = TransactionBulkUpdate(
        transaction_ids=[first_id, second_id],
        changes={"credit_card_id": credit_card_id},
    )
    service.repository.get_by_ids_for_update.return_value = [
        SimpleNamespace(
            id=first_id,
            account_id=uuid4(),
            credit_card_id=None,
            from_account_id=None,
            to_account_id=None,
        ),
        SimpleNamespace(
            id=second_id,
            account_id=None,
            credit_card_id=None,
            from_account_id=None,
            to_account_id=None,
        ),
    ]
    service.credit_card_service.get_user_unique_credit_card_with_filters = MagicMock(
        return_value=SimpleNamespace(id=credit_card_id)
    )

    with pytest.raises(HTTPException) as error:
        service.update_transactions_bulk(request, uuid4())

    assert error.value.status_code == 400
    service.repository.bulk_update_transactions.assert_not_called()
    db.rollback.assert_called_once_with()
