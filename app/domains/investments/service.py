from calendar import month_abbr
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, List, NamedTuple, Optional, Sequence, Tuple, cast
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.error_handlers import NotFoundError, ValidationError
from app.core.utils.date import add_months
from app.domains.accounts.models import Account
from app.domains.accounts.repository import AccountRepository
from app.domains.accounts.schemas import AccountType
from app.domains.balance_points.service import BalancePointService
from app.domains.balance_points.models import BalancePoint
from app.domains.investments.repository import InvestmentRepository, Movement
from app.domains.investments.schemas import (
    InvestmentBalanceListMeta,
    InvestmentBalanceListResponse,
    InvestmentBalanceResponse,
    InvestmentListMeta,
    InvestmentListResponse,
    InvestmentPortfolioResponse,
    InvestmentResponse,
    MonthlyBalanceSummary,
)

CENTS = Decimal("0.01")
ZERO = Decimal("0.00")
ONE_DAY = timedelta(days=1)


class Point(NamedTuple):
    date: date
    balance: Decimal


class MonthGrowth(NamedTuple):
    started_with: Decimal
    growth: Decimal


# ---- Pure calculations --------------------------------------------------------
#
# An investment's points are oldest first. The first is the opening: the
# balance at the start of its day, so transactions on that day come after it.
# Every later point is a balance at the end of its day, so transactions on that
# day are already inside it. (Same rule as the account balance.)


def percentage(part: Decimal, whole: Decimal) -> float:
    if whole == 0:
        return 0.0
    return float((part / whole * 100).quantize(CENTS, rounding=ROUND_HALF_UP))


def movement_between(
    movements: Sequence[Movement], start: Point, start_is_opening: bool, end: date
) -> Decimal:
    """Signed total of the transactions between two points."""
    first_day = start.date if start_is_opening else start.date + ONE_DAY
    return sum((amount for day, amount in movements if first_day <= day <= end), ZERO)


def compare_with_previous(
    points: Sequence[Point], index: int, movements: Sequence[Movement]
) -> Tuple[Decimal, Decimal, float]:
    """(movement, diff, diff %) of points[index] against the point before it."""
    previous, current = points[index - 1], points[index]
    movement = movement_between(movements, previous, index - 1 == 0, current.date)
    diff = (current.balance - previous.balance - movement).quantize(CENTS)
    return movement, diff, percentage(diff, previous.balance)


def summarize_month(
    year: int, month: int, points: Sequence[Point], movements: Sequence[Movement]
) -> MonthlyBalanceSummary:
    """One spreadsheet row: the month starts at the last point before it and
    ends at its last point."""
    first_day = date(year, month, 1)
    next_month = add_months(first_day, 1)
    start = next(
        (i for i in reversed(range(len(points))) if points[i].date < first_day), None
    )
    end = next(
        (
            i
            for i in reversed(range(len(points)))
            if first_day <= points[i].date < next_month
        ),
        None,
    )

    summary = MonthlyBalanceSummary(
        month=month,
        year=year,
        month_name=month_abbr[month],
        started_with=points[start].balance if start is not None else None,
        ended_with=points[end].balance if end is not None else None,
    )
    if start is None or end is None:
        summary.movement = sum(
            (amount for day, amount in movements if first_day <= day < next_month),
            ZERO,
        )
        return summary

    movement = movement_between(movements, points[start], start == 0, points[end].date)
    profit = (points[end].balance - points[start].balance - movement).quantize(CENTS)
    summary.movement = movement
    summary.profit = profit
    summary.profit_percentage = percentage(profit, points[start].balance)
    summary.has_data = True
    return summary


def total_invested(points: Sequence[Point], movements: Sequence[Movement]) -> Decimal:
    """The opening plus every income minus every expense."""
    opening = points[0].balance if points else ZERO
    return opening + sum((amount for _, amount in movements), ZERO)


def balance_at_end_of(
    last_day: date, points: Sequence[Point], movements: Sequence[Movement]
) -> Decimal:
    """The latest closing up to `last_day` plus the transactions after it; with
    no closing yet, the opening (once reached) plus every transaction. Same
    rule as the current account balance, stopped at `last_day`."""
    closings = [point for point in points[1:] if point.date <= last_day]
    if closings:
        latest = closings[-1]
        return latest.balance + sum(
            (amount for day, amount in movements if latest.date < day <= last_day),
            ZERO,
        )
    opening = points[0].balance if points and points[0].date <= last_day else ZERO
    return opening + sum((amount for day, amount in movements if day <= last_day), ZERO)


def invested_during(
    date_from: date,
    date_to: date,
    points: Sequence[Point],
    movements: Sequence[Movement],
) -> Decimal:
    """What the range starts with plus what went in during it: the balance at
    the end of the day before, every income minus every expense in the range,
    and the opening when the investment opened inside the range. Over the
    investment's whole life this is total_invested."""
    starts_with = balance_at_end_of(date_from - ONE_DAY, points, movements)
    moved = sum(
        (amount for day, amount in movements if date_from <= day <= date_to), ZERO
    )
    opened = (
        points[0].balance if points and date_from <= points[0].date <= date_to else ZERO
    )
    return starts_with + moved + opened


def growth_by_month(
    date_from: date,
    date_to: date,
    points: Sequence[Point],
    movements: Sequence[Movement],
) -> Dict[date, MonthGrowth]:
    """Each month with a saved balance inside the range, by its first day: what
    the market added that month (the diffs of those balances) and what the
    month started with (the balance saved before the first of them), as in the
    spreadsheet row."""
    months: Dict[date, MonthGrowth] = {}
    for index in range(1, len(points)):
        if not date_from <= points[index].date <= date_to:
            continue
        _, diff, _ = compare_with_previous(points, index, movements)
        month = points[index].date.replace(day=1)
        started_with, growth = months.get(
            month, MonthGrowth(points[index - 1].balance, ZERO)
        )
        months[month] = MonthGrowth(started_with, growth + diff)
    return months


def chained_percentage(investments: Sequence[Dict[date, MonthGrowth]]) -> float:
    """Each month's growth over what the month started with, the investments
    added together, compounded month after month. Money moved in a month is
    never growth, and only from the next month on is it part of what a month
    starts with, so deposits don't inflate or dilute the %."""
    started_with: Dict[date, Decimal] = defaultdict(lambda: ZERO)
    growth: Dict[date, Decimal] = defaultdict(lambda: ZERO)
    for months in investments:
        for month, values in months.items():
            started_with[month] += values.started_with
            growth[month] += values.growth

    factor = Decimal("1")
    for month in sorted(growth):
        if started_with[month] != 0:
            factor *= 1 + growth[month] / started_with[month]
    return float(((factor - 1) * 100).quantize(CENTS, rounding=ROUND_HALF_UP))


# ---- Service ------------------------------------------------------------------


def to_point(balance_point: BalancePoint) -> Point:
    return Point(cast(date, balance_point.date), cast(Decimal, balance_point.balance))


class InvestmentService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = InvestmentRepository(db)
        self.account_repository = AccountRepository(db)
        self.balance_point_service = BalancePointService(db)

    def get_monthly_summary(
        self, account_id: UUID, user_id: UUID, year: int, months: int
    ) -> List[MonthlyBalanceSummary]:
        """January to month `months` of `year`."""
        self._get_investment_account(account_id, user_id)
        points = [
            to_point(point)
            for point in self.repository.get_points_by_account([account_id]).get(
                account_id, []
            )
        ]
        movements = self.repository.get_movements_by_account([account_id], user_id)
        return [
            summarize_month(year, month, points, movements.get(account_id, []))
            for month in range(1, months + 1)
        ]

    def list_investments(
        self,
        user_id: UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> InvestmentListResponse:
        """Since each investment's opening; with a range, only that range: the
        balance at the end of `date_to`, what went in during the range, and the
        monthly growth % compounded over it."""
        if (date_from is None) != (date_to is None):
            raise ValidationError(
                message="Send both date_from and date_to, or neither",
                error_code="INCOMPLETE_DATE_RANGE",
            )
        if date_from is not None and date_to is not None and date_from > date_to:
            raise ValidationError(
                message="date_from can't be after date_to",
                error_code="INVALID_DATE_RANGE",
            )

        accounts = self.account_repository.get_by_user_and_status(
            user_id, is_active=True, account_type=AccountType.INVESTMENT
        )
        account_ids = [cast(UUID, account.id) for account in accounts]
        points_by_account = self.repository.get_points_by_account(account_ids)
        movements = self.repository.get_movements_by_account(account_ids, user_id)

        portfolios = []
        months_by_investment = []
        for account_id, account in zip(account_ids, accounts):
            balance_points = points_by_account.get(account_id, [])
            points = [to_point(point) for point in balance_points]
            account_movements = movements.get(account_id, [])
            if date_from is not None and date_to is not None:
                invested = invested_during(
                    date_from, date_to, points, account_movements
                )
                current_balance = balance_at_end_of(date_to, points, account_movements)
                months = growth_by_month(date_from, date_to, points, account_movements)
                months_by_investment.append(months)
                growth_percentage = chained_percentage([months])
            else:
                invested = total_invested(points, account_movements)
                current_balance = self.balance_point_service.calculate_account_balance(
                    account_id, user_id
                )
                growth_percentage = percentage(current_balance - invested, invested)
            growth = current_balance - invested
            last_updated = (
                cast(date, balance_points[-1].date)
                if balance_points
                else cast(datetime, account.updated_at).date()
            )
            portfolios.append(
                InvestmentPortfolioResponse(
                    investment=InvestmentResponse.model_validate(
                        account, from_attributes=True
                    ),
                    current_balance=current_balance,
                    total_invested=invested,
                    total_growth=growth,
                    growth_percentage=growth_percentage,
                    last_updated=last_updated,
                )
            )

        total_balance = sum((p.current_balance for p in portfolios), ZERO)
        total_growth = sum((p.total_growth for p in portfolios), ZERO)
        if date_from is not None and date_to is not None:
            overall_growth_percentage = chained_percentage(months_by_investment)
        else:
            overall_growth_percentage = percentage(
                total_growth, sum((p.total_invested for p in portfolios), ZERO)
            )
        return InvestmentListResponse(
            data=portfolios,
            meta=InvestmentListMeta(
                total=len(portfolios),
                total_balance=total_balance,
                total_growth=total_growth,
                overall_growth_percentage=overall_growth_percentage,
            ),
        )

    def list_balances(
        self,
        user_id: UUID,
        investment_id: Optional[UUID],
        date_from: Optional[date],
        date_to: Optional[date],
        sort_by: str,
        sort_order: str,
        page: int,
        per_page: int,
    ) -> InvestmentBalanceListResponse:
        """Every saved balance of the user's investments (or of one), each
        compared with the investment's previous balance."""
        if investment_id is not None:
            accounts: Sequence[Account] = [
                self._get_investment_account(investment_id, user_id)
            ]
        else:
            accounts = self.account_repository.get_by_user_and_status(
                user_id, is_active=True, account_type=AccountType.INVESTMENT
            )
        account_ids = [cast(UUID, account.id) for account in accounts]
        points_by_account = self.repository.get_points_by_account(account_ids)
        movements = self.repository.get_movements_by_account(account_ids, user_id)

        rows = []
        for account_id in account_ids:
            balance_points = points_by_account.get(account_id, [])
            points = [to_point(point) for point in balance_points]
            for index, balance_point in enumerate(balance_points):
                movement: Optional[Decimal] = None
                previous: Optional[Decimal] = None
                diff, diff_percentage = ZERO, 0.0
                if index > 0:
                    movement, diff, diff_percentage = compare_with_previous(
                        points, index, movements.get(account_id, [])
                    )
                    previous = points[index - 1].balance
                rows.append(
                    InvestmentBalanceResponse(
                        id=cast(UUID, balance_point.id),
                        investment_id=account_id,
                        date=points[index].date,
                        balance=points[index].balance,
                        # No money moved: the table shows "-" instead of 0.
                        movement_amount=movement or None,
                        previous_balance=previous,
                        diff_amount=diff,
                        diff_percentage=diff_percentage,
                        created_at=cast(datetime, balance_point.created_at),
                        updated_at=cast(datetime, balance_point.updated_at),
                    )
                )

        rows = [
            row
            for row in rows
            if (date_from is None or row.date >= date_from)
            and (date_to is None or row.date <= date_to)
        ]
        sort_keys = {
            "date": lambda row: (row.date, row.created_at),
            "balance": lambda row: (row.balance, row.date),
            "created_at": lambda row: (row.created_at, row.date),
        }
        rows.sort(key=sort_keys[sort_by], reverse=sort_order == "desc")

        total = len(rows)
        start = (page - 1) * per_page
        end = start + per_page
        return InvestmentBalanceListResponse(
            data=rows[start:end],
            meta=InvestmentBalanceListMeta(
                total=total,
                page=page,
                per_page=per_page,
                has_next=end < total,
                has_previous=page > 1,
            ),
        )

    def _get_investment_account(self, account_id: UUID, user_id: UUID) -> Account:
        account = self.account_repository.get_by_id_and_user(account_id, user_id)
        if account is None:
            raise NotFoundError(
                message="Account not found", error_code="ACCOUNT_NOT_FOUND"
            )
        if account.type != AccountType.INVESTMENT.value:
            raise ValidationError(
                message="This is only available for investment accounts",
                error_code="NOT_AN_INVESTMENT_ACCOUNT",
            )
        return account
