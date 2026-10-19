from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, Generator, List, NamedTuple, Optional, cast
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.error_handlers import NotFoundError, ValidationError
from app.domains.accounts.repository import AccountRepository
from app.domains.accounts.schemas import AccountType
from app.domains.balance_points.constants import TimelineStatus
from app.domains.balance_points.models import BalancePoint
from app.domains.balance_points.repository import BalancePointRepository
from app.domains.transactions.constants import MovementType
from app.domains.transactions.models import Transaction
from app.domains.transactions.repository import TransactionRepository

ONE_DAY = timedelta(days=1)


class Point(NamedTuple):
    date: date
    balance: Decimal


def signed_amount(transaction: Transaction) -> Decimal:
    """Same rule as transactions.repository.signed_amount, for loaded rows."""
    amount = cast(Decimal, transaction.amount)
    if transaction.movement_type in (MovementType.INCOME, MovementType.INVESTMENT):
        return amount
    return -amount


class BalancePointService:
    """
    An account's balance points, oldest first:

    - The first is the opening anchor, created with the account. It is the
      balance at the start of its day, and every transaction of the account
      counts on top of it.
    - Any later point is a closing: the balance observed at the end of its day
      (for an investment, what the broker shows at month end). Transactions up
      to that day are already inside it.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repository = BalancePointRepository(db)
        self.transaction_repository = TransactionRepository(db)
        self.account_repository = AccountRepository(db)

    def calculate_account_balance(self, account_id: UUID, user_id: UUID) -> Decimal:
        """Current balance: the latest closing plus the transactions after its
        day; with no closing, the opening plus all transactions."""
        opening, closings = self._points(account_id, user_id)

        if closings:
            latest = closings[-1]
            return latest.balance + self.transaction_repository.get_balance_between(
                account_id, user_id, date_from=latest.date + ONE_DAY
            )

        opening_balance = opening.balance if opening else Decimal("0.00")
        return opening_balance + self.transaction_repository.get_balance_between(
            account_id, user_id
        )

    def create_opening_balance_point(
        self,
        account_id: UUID,
        opening_date: date,
        opening_balance: Decimal,
        commit: bool = True,
    ) -> BalancePoint:
        """Persist the initial balance anchor created with an account."""
        return self.repository.create_balance_point(
            {
                "account_id": account_id,
                "date": opening_date,
                "balance": opening_balance,
                "timeline_status": TimelineStatus.CURRENT.value,
                "has_transactions": False,
            },
            commit=commit,
        )

    def save_closing(
        self, account_id: UUID, user_id: UUID, closing_date: date, balance: Decimal
    ) -> BalancePoint:
        """Record an investment account's balance at the end of a day. Saving
        the same date again replaces the value. An account created without an
        opening balance gets its first saved balance as the opening."""
        account = self.account_repository.get_by_id_and_user(account_id, user_id)
        if account is None:
            raise NotFoundError(
                message="Account not found", error_code="ACCOUNT_NOT_FOUND"
            )
        if account.type != AccountType.INVESTMENT.value:
            raise ValidationError(
                message="Balances can only be recorded on investment accounts",
                error_code="NOT_AN_INVESTMENT_ACCOUNT",
            )
        if closing_date > date.today():
            raise ValidationError(
                message="A balance can't be in the future",
                error_code="CLOSING_IN_FUTURE",
            )

        opening, _ = self._points(account_id, user_id)
        if opening is not None and closing_date < opening.date:
            raise ValidationError(
                message=f"A balance can't be before the opening date ({opening.date})",
                error_code="CLOSING_BEFORE_OPENING",
            )

        return self.repository.upsert_balance_point(account_id, closing_date, balance)

    def _points(
        self, account_id: UUID, user_id: UUID
    ) -> tuple[Optional[Point], List[Point]]:
        """The account's opening point and its closings, oldest first."""
        points = [
            Point(cast(date, point.date), cast(Decimal, point.balance))
            for point in self.repository.get_balance_points(account_id, user_id)
        ]
        if not points:
            return None, []
        return points[0], points[1:]

    def group_transactions_by_date(
        self, transactions: List[Transaction]
    ) -> Dict[date, List[Transaction]]:
        transactions_by_date: Dict[date, List[Transaction]] = {}
        for transaction in transactions:
            transactions_by_date.setdefault(transaction.date.date(), []).append(
                transaction
            )
        return transactions_by_date

    def calculate_balance_timeline(
        self,
        account_id: UUID,
        user_id: UUID,
        start_date: date,
        end_date: date,
    ) -> List[Dict[str, Any]]:
        """
        The end-of-day balance for each day in the range, using the same rule
        as calculate_account_balance: a closing replaces the running balance at
        the end of its day.
        """
        opening, closings = self._points(account_id, user_id)
        closing_by_date = {closing.date: closing.balance for closing in closings}

        current_balance = self._balance_at_start_of(
            account_id, user_id, start_date, opening, closings
        )
        transactions_by_date = self.group_transactions_by_date(
            self.transaction_repository.get_transactions_for_timeline(
                account_id, user_id, start_date, end_date
            )
        )

        balance_points = []
        for current_date in self.date_range_iterator(start_date, end_date):
            if opening and current_date == opening.date:
                current_balance += opening.balance

            current_balance += sum(
                (
                    signed_amount(transaction)
                    for transaction in transactions_by_date.get(current_date, [])
                ),
                Decimal("0.00"),
            )

            if current_date in closing_by_date:
                current_balance = closing_by_date[current_date]

            # Return plain dict - FastAPI will convert to Pydantic schema
            balance_points.append(
                {
                    "account_id": account_id,
                    "date": current_date,
                    "balance": current_balance,
                }
            )
        return balance_points

    def _balance_at_start_of(
        self,
        account_id: UUID,
        user_id: UUID,
        day: date,
        opening: Optional[Point],
        closings: List[Point],
    ) -> Decimal:
        earlier_closings = [closing for closing in closings if closing.date < day]
        if earlier_closings:
            latest = earlier_closings[-1]
            return latest.balance + self.transaction_repository.get_balance_between(
                account_id, user_id, date_from=latest.date + ONE_DAY, date_to=day
            )

        balance = self.transaction_repository.get_balance_between(
            account_id, user_id, date_to=day
        )
        if opening and opening.date < day:
            balance += opening.balance
        return balance

    def date_range_iterator(
        self, start_date: date, end_date: date
    ) -> Generator[date, None, None]:
        current_date = start_date

        while current_date <= end_date:
            yield current_date
            current_date += ONE_DAY
