from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from app.domains.transactions.repository import TransactionRepository


def build_repository_with_transaction(transaction):
    db = MagicMock()
    query = MagicMock()
    db.query.return_value = query
    query.options.return_value = query
    query.filter.return_value = query
    query.first.return_value = transaction
    return TransactionRepository(db), db


def test_update_transaction_preserves_explicit_null_fields():
    transaction = SimpleNamespace(
        account_id=uuid4(),
        credit_card_id=None,
        updated_at=None,
    )
    repository, db = build_repository_with_transaction(transaction)
    new_credit_card_id = uuid4()

    result = repository.update_transaction(
        transaction_id=uuid4(),
        user_id=uuid4(),
        update_data={
            "account_id": None,
            "credit_card_id": new_credit_card_id,
        },
    )

    assert result is transaction
    assert result.account_id is None
    assert result.credit_card_id == new_credit_card_id
    assert result.updated_at is not None
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(transaction)


def test_update_transaction_leaves_omitted_fields_unchanged():
    vendor_id = uuid4()
    transaction = SimpleNamespace(
        description="Original description",
        vendor_id=vendor_id,
        updated_at=None,
    )
    repository, _ = build_repository_with_transaction(transaction)

    result = repository.update_transaction(
        transaction_id=uuid4(),
        user_id=uuid4(),
        update_data={"vendor_id": None},
    )

    assert result.vendor_id is None
    assert result.description == "Original description"


def test_bulk_update_transactions_flushes_all_rows_without_committing():
    first = SimpleNamespace(id=uuid4(), tags=[], updated_at=None)
    second = SimpleNamespace(id=uuid4(), tags=[], updated_at=None)
    db = MagicMock()
    repository = TransactionRepository(db)
    tags = [SimpleNamespace(id=uuid4())]
    repository.get_by_ids = MagicMock(return_value=[first, second])

    result = repository.bulk_update_transactions(
        transactions=[first, second],
        user_id=uuid4(),
        update_data={"tags": tags},
    )

    assert result == [first, second]
    assert first.tags == tags
    assert second.tags == tags
    assert first.updated_at == second.updated_at
    db.flush.assert_called_once_with()
    db.commit.assert_not_called()
    db.rollback.assert_not_called()
