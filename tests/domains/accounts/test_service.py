from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.domains.accounts.schemas import AccountCreateIn, AccountType
from app.domains.accounts.service import AccountService


def build_account_input(balance: float = 1000.0) -> AccountCreateIn:
    return AccountCreateIn(
        name="Checking",
        type=AccountType.CASH,
        currency="BRL",
        broker_id=uuid4(),
        balance=balance,
    )


def test_create_account_atomically_creates_opening_balance_point():
    db = MagicMock()
    service = AccountService(db)
    service.repository = MagicMock()
    service.balance_point_service = MagicMock()
    user_id = uuid4()
    account = SimpleNamespace(
        id=uuid4(),
        created_at=datetime(2026, 1, 2, 10, 30),
    )
    service.repository.exists_by_name_and_user.return_value = False
    service.repository.create.return_value = account
    service.repository.get_by_id_and_user.return_value = account

    result = service.create_account(build_account_input(), user_id)

    assert result is account
    account_data = service.repository.create.call_args.args[0]
    assert "balance" not in account_data
    assert account_data["user_id"] == user_id
    service.repository.create.assert_called_once_with(account_data, commit=False)
    service.balance_point_service.create_opening_balance_point.assert_called_once()
    opening_call = (
        service.balance_point_service.create_opening_balance_point.call_args.kwargs
    )
    assert opening_call["account_id"] == account.id
    assert opening_call["opening_date"] == account.created_at.date()
    assert str(opening_call["opening_balance"]) == "1000.0"
    assert opening_call["commit"] is False
    db.commit.assert_called_once()
    db.rollback.assert_not_called()


def test_create_account_rolls_back_if_opening_point_fails():
    db = MagicMock()
    service = AccountService(db)
    service.repository = MagicMock()
    service.balance_point_service = MagicMock()
    service.repository.exists_by_name_and_user.return_value = False
    service.repository.create.return_value = SimpleNamespace(
        id=uuid4(),
        created_at=datetime(2026, 1, 2, 10, 30),
    )
    service.balance_point_service.create_opening_balance_point.side_effect = (
        RuntimeError("opening point failed")
    )

    with pytest.raises(RuntimeError, match="opening point failed"):
        service.create_account(build_account_input(), uuid4())

    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_create_account_uses_the_given_opening_date():
    db = MagicMock()
    service = AccountService(db)
    service.repository = MagicMock()
    service.balance_point_service = MagicMock()
    account = SimpleNamespace(id=uuid4(), created_at=datetime(2026, 1, 2, 10, 30))
    service.repository.exists_by_name_and_user.return_value = False
    service.repository.create.return_value = account
    service.repository.get_by_id_and_user.return_value = account
    account_in = build_account_input()
    account_in.opening_date = date(2022, 12, 31)

    service.create_account(account_in, uuid4())

    assert "opening_date" not in service.repository.create.call_args.args[0]
    opening_call = (
        service.balance_point_service.create_opening_balance_point.call_args.kwargs
    )
    assert opening_call["opening_date"] == date(2022, 12, 31)


def test_opening_date_cannot_be_in_the_future():
    with pytest.raises(ValueError, match="opening_date"):
        AccountCreateIn(
            name="Previdência",
            type=AccountType.INVESTMENT,
            broker_id=uuid4(),
            opening_date=date.today() + timedelta(days=1),
        )
