from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domains.transactions.schemas import TransactionBulkUpdate, TransactionResponse


def build_transaction(**overrides):
    now = datetime.utcnow()
    data = {
        "id": uuid4(),
        "user_id": uuid4(),
        "account_id": uuid4(),
        "credit_card_id": None,
        "from_account_id": None,
        "to_account_id": None,
        "broker_id": uuid4(),
        "is_paid": False,
        "date": now,
        "amount": 19.9,
        "description": "Estadao",
        "movement_type": "expense",
        "tag_ids": [],
        "tags": [],
        "ignored": False,
        "vendor_id": None,
        "subscription_id": None,
        "installment_id": None,
        "is_deleted": False,
        "created_at": now,
        "updated_at": now,
        "account": None,
        "credit_card": None,
        "vendor": None,
        "subscription": None,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_transaction_response_includes_direct_account_name():
    transaction = build_transaction(
        account=SimpleNamespace(id=uuid4(), name="Nubank Checking"),
    )

    result = TransactionResponse.from_orm(transaction)

    assert result.account_name == "Nubank Checking"
    assert result.credit_card_name is None


def test_transaction_response_includes_credit_card_and_bank_account_names():
    bank_account_id = uuid4()
    transaction = build_transaction(
        account_id=None,
        credit_card_id=uuid4(),
        credit_card=SimpleNamespace(
            id=uuid4(),
            name="Nubank Ultravioleta",
            account_id=bank_account_id,
            account=SimpleNamespace(id=bank_account_id, name="Nubank Checking"),
        ),
    )

    result = TransactionResponse.from_orm(transaction)

    assert result.account_id == bank_account_id
    assert result.account_name == "Nubank Checking"
    assert result.credit_card_name == "Nubank Ultravioleta"
    assert transaction.account_id is None


def test_bulk_update_preserves_explicit_null_change():
    request = TransactionBulkUpdate(
        transaction_ids=[uuid4()],
        changes={"vendor_id": None},
    )

    assert request.changes.model_dump(exclude_unset=True) == {"vendor_id": None}


def test_bulk_update_rejects_duplicate_transaction_ids():
    transaction_id = uuid4()

    with pytest.raises(ValidationError, match="must not contain duplicates"):
        TransactionBulkUpdate(
            transaction_ids=[transaction_id, transaction_id],
            changes={"tag_ids": [uuid4()]},
        )


def test_bulk_update_rejects_empty_changes():
    with pytest.raises(ValidationError, match="at least one field"):
        TransactionBulkUpdate(
            transaction_ids=[uuid4()],
            changes={},
        )
