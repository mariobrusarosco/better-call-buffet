from calendar import month_abbr
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import List, Optional, Sequence, cast
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.error_handlers import NotFoundError, ValidationError
from app.core.utils.date import add_months
from app.domains.accounts.models import Account
from app.domains.accounts.repository import AccountRepository
from app.domains.accounts.schemas import AccountType
from app.domains.investments.repository import InvestmentRepository, Movements, Points
from app.domains.investments.schemas import (
    InvestmentAccountPerformance,
    InvestmentPortfolioResponse,
    MonthlyBalanceSummary,
)

CENTS = Decimal("0.01")
ZERO = Decimal("0.00")
MAX_MONTHS = 120


# ---- Pure calculations --------------------------------------------------------


def month_range(first_month: date, last_month: date) -> List[date]:
    """The first day of every month from first_month to last_month, inclusive."""
    months = []
    month = first_month
    while month <= last_month:
        months.append(month)
        month = add_months(month, 1)
    return months


def percentage(part: Decimal, whole: Decimal) -> Optional[Decimal]:
    if whole == 0:
        return None
    return (part / whole * 100).quantize(CENTS, rounding=ROUND_HALF_UP)


def summarize_month(
    month: date, points: Points, movements: Movements
) -> MonthlyBalanceSummary:
    """One spreadsheet row. The month's closing is its last balance point; the
    start is the last balance point before the month (the previous closing, or
    the opening). Movement is the signed total of the month's transactions."""
    next_month = add_months(month, 1)
    started_with = next(
        (balance for day, balance in reversed(points) if day < month), None
    )
    ended_with = next(
        (balance for day, balance in reversed(points) if month <= day < next_month),
        None,
    )
    movement = movements.get(month.strftime("%Y-%m"), ZERO)

    summary = MonthlyBalanceSummary(
        month=month.strftime("%Y-%m"),
        month_name=month_abbr[month.month],
        started_with=started_with,
        ended_with=ended_with,
        movement=movement,
    )
    if started_with is not None and ended_with is not None:
        profit = (ended_with - started_with - movement).quantize(CENTS)
        summary.profit = profit
        summary.profit_percentage = percentage(profit, started_with)
        summary.has_data = True
    return summary


def summarize_months(
    months: Sequence[date], points: Points, movements: Movements
) -> List[MonthlyBalanceSummary]:
    return [summarize_month(month, points, movements) for month in months]


def total_month(
    month: date, rows: Sequence[MonthlyBalanceSummary]
) -> MonthlyBalanceSummary:
    """The portfolio row for one month, over the accounts that have data for
    it. Like the spreadsheet's Net Worth row, its % is profit ÷ closing."""
    total = summarize_month(month, [], {})
    with_data = [row for row in rows if row.has_data]
    if not with_data:
        return total

    # Rows with data always have both balances and a profit.
    ended_with = sum((row.ended_with or ZERO for row in with_data), ZERO)
    profit = sum((row.profit or ZERO for row in with_data), ZERO)
    total.started_with = sum((row.started_with or ZERO for row in with_data), ZERO)
    total.ended_with = ended_with
    total.movement = sum((row.movement for row in with_data), ZERO)
    total.profit = profit
    total.profit_percentage = percentage(profit, ended_with)
    total.has_data = True
    return total


# ---- Service ------------------------------------------------------------------


class InvestmentService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = InvestmentRepository(db)
        self.account_repository = AccountRepository(db)

    def get_monthly_performance(
        self, account_id: UUID, user_id: UUID, first_month: date, last_month: date
    ) -> List[MonthlyBalanceSummary]:
        months = self._months(first_month, last_month)
        account = self.account_repository.get_by_id_and_user(account_id, user_id)
        if account is None:
            raise NotFoundError(
                message="Account not found", error_code="ACCOUNT_NOT_FOUND"
            )
        if account.type != AccountType.INVESTMENT.value:
            raise ValidationError(
                message="Monthly performance is only available for investment accounts",
                error_code="NOT_AN_INVESTMENT_ACCOUNT",
            )

        performance = self._performance([account], user_id, months)
        return performance[0].months

    def get_portfolio(
        self, user_id: UUID, first_month: date, last_month: date
    ) -> InvestmentPortfolioResponse:
        months = self._months(first_month, last_month)
        accounts = self.account_repository.get_by_user_and_status(
            user_id, is_active=True, account_type=AccountType.INVESTMENT
        )
        performance = self._performance(accounts, user_id, months)

        totals = [
            total_month(month, [account.months[index] for account in performance])
            for index, month in enumerate(months)
        ]
        return InvestmentPortfolioResponse(accounts=performance, totals=totals)

    def _performance(
        self, accounts: Sequence[Account], user_id: UUID, months: Sequence[date]
    ) -> List[InvestmentAccountPerformance]:
        account_ids = [cast(UUID, account.id) for account in accounts]
        if not account_ids:
            return []

        points = self.repository.get_points_by_account(account_ids)
        movements = self.repository.get_movements_by_account(
            account_ids, user_id, months[0], add_months(months[-1], 1)
        )
        return [
            InvestmentAccountPerformance(
                account_id=account_id,
                name=cast(str, account.name),
                broker=account.broker,
                months=summarize_months(
                    months, points.get(account_id, []), movements.get(account_id, {})
                ),
            )
            for account_id, account in zip(account_ids, accounts)
        ]

    @staticmethod
    def _months(first_month: date, last_month: date) -> List[date]:
        if first_month > last_month:
            raise ValidationError(
                message="'from' must be on or before 'to'",
                error_code="INVALID_MONTH_RANGE",
            )
        months = month_range(first_month, last_month)
        if len(months) > MAX_MONTHS:
            raise ValidationError(
                message=f"At most {MAX_MONTHS} months per request",
                error_code="MONTH_RANGE_TOO_LONG",
            )
        return months
