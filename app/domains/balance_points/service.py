from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, Generator, List
from uuid import UUID

from sqlalchemy.orm import Session

from app.domains.balance_points.constants import TimelineStatus
from app.domains.balance_points.models import BalancePoint
from app.domains.balance_points.repository import BalancePointRepository
from app.domains.transactions.constants import MovementType
from app.domains.transactions.models import Transaction
from app.domains.transactions.repository import TransactionRepository


class BalancePointService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = BalancePointRepository(db)
        self.transaction_repository = TransactionRepository(db)

    def calculate_account_balance_from_transactions(
        self, account_id: UUID, user_id: UUID
    ) -> Decimal:
        """
        Calculate account balance from its opening point and all transactions.

        The first persisted balance point is the opening anchor. All later
        movement is calculated from transactions using the timeline rules:
        - income/investment: positive (adds to balance)
        - expense/transfer/other: negative (subtracts from balance)

        Args:
            account_id: The account to calculate balance for
            user_id: The user who owns the account

        Returns:
            Decimal: Opening balance plus the signed transaction total
        """
        opening_point = self.repository.get_opening_balance_point(account_id, user_id)
        opening_balance = opening_point.balance if opening_point else Decimal("0.00")
        transaction_balance = self.transaction_repository.get_account_total_balance(
            account_id, user_id
        )
        return opening_balance + transaction_balance

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

    def group_transactions_by_date(
        self, transactions: List[Transaction]
    ) -> Dict[date, List[Transaction]]:
        transactions_by_date = {}
        for transaction in transactions:
            date = transaction.date.date()
            if date not in transactions_by_date:
                transactions_by_date[date] = []
            transactions_by_date[date].append(transaction)
        return transactions_by_date

    def calculate_balance_timeline(
        self,
        account_id: UUID,
        user_id: UUID,
        start_date: date,
        end_date: date,
    ) -> List[Dict[str, Any]]:
        """
        Calculate the balance timeline for a given account and date range.
        """

        previous_balance = self.transaction_repository.get_balance_before_date(
            account_id, user_id, start_date
        )
        transactions = self.transaction_repository.get_transactions_for_timeline(
            account_id, user_id, start_date, end_date
        )
        transactions_by_date = self.group_transactions_by_date(transactions)

        opening_point = self.repository.get_opening_balance_point(account_id, user_id)

        current_balance = previous_balance
        if opening_point and opening_point.date < start_date:
            current_balance += opening_point.balance
        balance_points = []

        for current_date in self.date_range_iterator(start_date, end_date):
            if opening_point and current_date == opening_point.date:
                current_balance += opening_point.balance

            transactions_of_day = transactions_by_date.get(current_date, [])

            summed_transactions_of_day = sum(
                (
                    (
                        transaction.amount
                        if transaction.movement_type
                        in [MovementType.INCOME, MovementType.INVESTMENT]
                        else -transaction.amount
                    )
                    for transaction in transactions_of_day
                ),
                Decimal("0.00"),
            )
            current_balance += summed_transactions_of_day

            # Return plain dict - FastAPI will convert to Pydantic schema
            balance_points.append(
                {
                    "account_id": account_id,
                    "date": current_date,
                    "balance": current_balance,
                }
            )
        return balance_points

    def date_range_iterator(
        self, start_date: date, end_date: date
    ) -> Generator[date, None, None]:
        current_date = start_date

        while current_date <= end_date:
            yield current_date
            current_date += timedelta(days=1)
