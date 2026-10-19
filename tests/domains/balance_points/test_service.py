from datetime import date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.core.error_handlers import NotFoundError, ValidationError
from app.domains.balance_points.service import BalancePointService
from app.domains.transactions.constants import MovementType


def build_service() -> BalancePointService:
    service = BalancePointService(MagicMock())
    service.repository = MagicMock()
    service.transaction_repository = MagicMock()
    service.account_repository = MagicMock()
    return service


def point(day: date, balance: str) -> SimpleNamespace:
    return SimpleNamespace(date=day, balance=Decimal(balance))


# ---- Current balance ------------------------------------------------------------


def test_current_balance_adds_all_transactions_to_the_opening_point():
    service = build_service()
    account_id, user_id = uuid4(), uuid4()
    service.repository.get_balance_points.return_value = [
        point(date(2026, 1, 1), "1000.00")
    ]
    service.transaction_repository.get_balance_between.return_value = Decimal("-125.50")

    balance = service.calculate_account_balance(account_id, user_id)

    assert balance == Decimal("874.50")
    service.transaction_repository.get_balance_between.assert_called_once_with(
        account_id, user_id
    )


def test_current_balance_is_the_transactions_when_opening_point_is_missing():
    service = build_service()
    service.repository.get_balance_points.return_value = []
    service.transaction_repository.get_balance_between.return_value = Decimal("25.00")

    assert service.calculate_account_balance(uuid4(), uuid4()) == Decimal("25.00")


def test_current_balance_starts_from_the_latest_closing():
    """Transactions up to the closing day are inside the closing; only later
    ones add to it."""
    service = build_service()
    account_id, user_id = uuid4(), uuid4()
    service.repository.get_balance_points.return_value = [
        point(date(2025, 12, 31), "11036.00"),
        point(date(2026, 1, 31), "11196.00"),
        point(date(2026, 2, 28), "11451.00"),
    ]
    service.transaction_repository.get_balance_between.return_value = Decimal("500.00")

    balance = service.calculate_account_balance(account_id, user_id)

    assert balance == Decimal("11951.00")
    service.transaction_repository.get_balance_between.assert_called_once_with(
        account_id, user_id, date_from=date(2026, 3, 1)
    )


# ---- Timeline -------------------------------------------------------------------


def test_timeline_applies_opening_point_on_its_date_then_carries_balance_forward():
    service = build_service()
    service.repository.get_balance_points.return_value = [
        point(date(2026, 1, 2), "1000.00")
    ]
    service.transaction_repository.get_balance_between.return_value = Decimal("0.00")
    service.transaction_repository.get_transactions_for_timeline.return_value = [
        SimpleNamespace(
            date=datetime(2026, 1, 3, 12, 0),
            amount=Decimal("100.00"),
            movement_type=MovementType.EXPENSE,
        )
    ]

    timeline = service.calculate_balance_timeline(
        account_id=uuid4(),
        user_id=uuid4(),
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 4),
    )

    assert [entry["balance"] for entry in timeline] == [
        Decimal("0.00"),
        Decimal("1000.00"),
        Decimal("900.00"),
        Decimal("900.00"),
    ]


def test_timeline_includes_opening_point_when_range_starts_later():
    service = build_service()
    service.repository.get_balance_points.return_value = [
        point(date(2026, 1, 1), "1000.00")
    ]
    service.transaction_repository.get_balance_between.return_value = Decimal("-200.00")
    service.transaction_repository.get_transactions_for_timeline.return_value = []

    timeline = service.calculate_balance_timeline(
        account_id=uuid4(),
        user_id=uuid4(),
        start_date=date(2026, 1, 10),
        end_date=date(2026, 1, 10),
    )

    assert timeline[0]["balance"] == Decimal("800.00")


def test_timeline_replaces_the_balance_with_a_closing_at_the_end_of_its_day():
    service = build_service()
    service.repository.get_balance_points.return_value = [
        point(date(2026, 1, 1), "1000.00"),
        point(date(2026, 1, 3), "1500.00"),
    ]
    service.transaction_repository.get_balance_between.return_value = Decimal("0.00")
    service.transaction_repository.get_transactions_for_timeline.return_value = [
        SimpleNamespace(
            date=datetime(2026, 1, 3, 9, 0),
            amount=Decimal("100.00"),
            movement_type=MovementType.INCOME,
        ),
        SimpleNamespace(
            date=datetime(2026, 1, 4, 9, 0),
            amount=Decimal("50.00"),
            movement_type=MovementType.INCOME,
        ),
    ]

    timeline = service.calculate_balance_timeline(
        account_id=uuid4(),
        user_id=uuid4(),
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 4),
    )

    assert [entry["balance"] for entry in timeline] == [
        Decimal("1000.00"),
        Decimal("1000.00"),
        Decimal("1500.00"),
        Decimal("1550.00"),
    ]


def test_timeline_starting_after_a_closing_starts_from_that_closing():
    service = build_service()
    account_id, user_id = uuid4(), uuid4()
    service.repository.get_balance_points.return_value = [
        point(date(2026, 1, 1), "1000.00"),
        point(date(2026, 1, 31), "1500.00"),
    ]
    service.transaction_repository.get_balance_between.return_value = Decimal("200.00")
    service.transaction_repository.get_transactions_for_timeline.return_value = []

    timeline = service.calculate_balance_timeline(
        account_id=account_id,
        user_id=user_id,
        start_date=date(2026, 2, 10),
        end_date=date(2026, 2, 10),
    )

    assert timeline[0]["balance"] == Decimal("1700.00")
    service.transaction_repository.get_balance_between.assert_called_once_with(
        account_id, user_id, date_from=date(2026, 2, 1), date_to=date(2026, 2, 10)
    )


# ---- Closings -------------------------------------------------------------------


def build_investment_service(account_type: str = "investment") -> BalancePointService:
    service = build_service()
    service.account_repository.get_by_id_and_user.return_value = SimpleNamespace(
        type=account_type
    )
    service.repository.get_balance_points.return_value = [
        point(date(2025, 12, 31), "11036.00")
    ]
    return service


def test_save_closing_upserts_the_balance_on_that_date():
    service = build_investment_service()
    account_id = uuid4()

    service.save_closing(account_id, uuid4(), date(2026, 1, 31), Decimal("11196.00"))

    service.repository.upsert_balance_point.assert_called_once_with(
        account_id, date(2026, 1, 31), Decimal("11196.00")
    )


def test_save_closing_rejects_accounts_that_are_not_investments():
    service = build_investment_service(account_type="cash")

    with pytest.raises(ValidationError) as error:
        service.save_closing(uuid4(), uuid4(), date(2026, 1, 31), Decimal("1"))

    assert error.value.error_code == "NOT_AN_INVESTMENT_ACCOUNT"
    service.repository.upsert_balance_point.assert_not_called()


def test_save_closing_rejects_an_unknown_account():
    service = build_service()
    service.account_repository.get_by_id_and_user.return_value = None

    with pytest.raises(NotFoundError):
        service.save_closing(uuid4(), uuid4(), date(2026, 1, 31), Decimal("1"))


def test_save_closing_rejects_future_dates():
    service = build_investment_service()

    with pytest.raises(ValidationError) as error:
        service.save_closing(
            uuid4(), uuid4(), date.today() + timedelta(days=1), Decimal("1")
        )

    assert error.value.error_code == "CLOSING_IN_FUTURE"


def test_save_closing_rejects_dates_before_the_opening():
    service = build_investment_service()

    with pytest.raises(ValidationError) as error:
        service.save_closing(uuid4(), uuid4(), date(2025, 12, 30), Decimal("1"))

    assert error.value.error_code == "CLOSING_BEFORE_OPENING"


def test_first_balance_on_an_account_without_opening_becomes_the_opening():
    """Accounts created before opening balances existed have no points."""
    service = build_investment_service()
    service.repository.get_balance_points.return_value = []
    account_id = uuid4()

    service.save_closing(account_id, uuid4(), date(2022, 12, 31), Decimal("28799.00"))

    service.repository.upsert_balance_point.assert_called_once_with(
        account_id, date(2022, 12, 31), Decimal("28799.00")
    )
