from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from app.domains.balance_points.service import BalancePointService
from app.domains.transactions.constants import MovementType


def build_service() -> BalancePointService:
    service = BalancePointService(MagicMock())
    service.repository = MagicMock()
    service.transaction_repository = MagicMock()
    return service


def test_current_balance_adds_transactions_to_opening_balance_point():
    service = build_service()
    account_id = uuid4()
    user_id = uuid4()
    service.repository.get_opening_balance_point.return_value = SimpleNamespace(
        balance=Decimal("1000.00"),
        date=date(2026, 1, 1),
    )
    service.transaction_repository.get_account_total_balance.return_value = Decimal(
        "-125.50"
    )

    balance = service.calculate_account_balance_from_transactions(account_id, user_id)

    assert balance == Decimal("874.50")


def test_current_balance_defaults_to_transactions_when_opening_point_is_missing():
    service = build_service()
    service.repository.get_opening_balance_point.return_value = None
    service.transaction_repository.get_account_total_balance.return_value = Decimal(
        "25.00"
    )

    balance = service.calculate_account_balance_from_transactions(uuid4(), uuid4())

    assert balance == Decimal("25.00")


def test_timeline_applies_opening_point_on_its_date_then_carries_balance_forward():
    service = build_service()
    account_id = uuid4()
    user_id = uuid4()
    service.repository.get_opening_balance_point.return_value = SimpleNamespace(
        balance=Decimal("1000.00"),
        date=date(2026, 1, 2),
    )
    service.transaction_repository.get_balance_before_date.return_value = Decimal(
        "0.00"
    )
    service.transaction_repository.get_transactions_for_timeline.return_value = [
        SimpleNamespace(
            date=datetime(2026, 1, 3, 12, 0),
            amount=Decimal("100.00"),
            movement_type=MovementType.EXPENSE,
        )
    ]

    timeline = service.calculate_balance_timeline(
        account_id=account_id,
        user_id=user_id,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 4),
    )

    assert [point["balance"] for point in timeline] == [
        Decimal("0.00"),
        Decimal("1000.00"),
        Decimal("900.00"),
        Decimal("900.00"),
    ]


def test_timeline_includes_opening_point_when_range_starts_later():
    service = build_service()
    service.repository.get_opening_balance_point.return_value = SimpleNamespace(
        balance=Decimal("1000.00"),
        date=date(2026, 1, 1),
    )
    service.transaction_repository.get_balance_before_date.return_value = Decimal(
        "-200.00"
    )
    service.transaction_repository.get_transactions_for_timeline.return_value = []

    timeline = service.calculate_balance_timeline(
        account_id=uuid4(),
        user_id=uuid4(),
        start_date=date(2026, 1, 10),
        end_date=date(2026, 1, 10),
    )

    assert timeline[0]["balance"] == Decimal("800.00")
