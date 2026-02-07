from datetime import date, timedelta
from typing import Generator, List, Dict, Any
from uuid import UUID
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domains.balance_points.repository import BalancePointRepository
from app.domains.transactions.repository import TransactionRepository
from app.domains.transactions.models import Transaction
from app.domains.transactions.constants import MovementType


class BalancePointService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = BalancePointRepository(db)
        self.transaction_repository = TransactionRepository(db)

    def calculate_account_balance_from_transactions(
        self, account_id: UUID, user_id: UUID
    ) -> Decimal:
        """
        STUB: Calculate account balance from transactions.

        TODO: Implement in Phase 3 - Service Layer Logic
        For now, returns 0.00 to prevent errors.

        Args:
            account_id: The account to calculate balance for
            user_id: The user who owns the account

        Returns:
            Decimal: Account balance (currently stub returns 0.00)
        """
        # Temporary stub - return 0.00
        # Will be implemented in Phase 3 when we build timeline calculation
        return Decimal('0.00')

    def group_transactions_by_date(self, transactions: List[Transaction]) -> Dict[date, List[Transaction]]:
        transactions_by_date = {}
        for transaction in transactions:
            date = transaction.date.date()
            if date not in transactions_by_date:
                transactions_by_date[date] = []
            transactions_by_date[date].append(transaction)
        return transactions_by_date

    def calculate_balance_timeline(
        self, account_id: UUID, user_id: UUID, start_date: date, end_date: date,
    ) -> List[Dict[str, Any]]:
        """
        Calculate the balance timeline for a given account and date range.
        """

        previous_balance = self.transaction_repository.get_balance_before_date(account_id, user_id, start_date)
        transactions= self.transaction_repository.get_transactions_for_timeline(account_id, user_id, start_date, end_date)
        transactions_by_date = self.group_transactions_by_date(transactions)

        current_balance = previous_balance
        balance_points = []

        for date in self.date_range_iterator(start_date, end_date):
            transactions_of_day = transactions_by_date.get(date, [])

            summed_transactions_of_day = sum(
                transaction.amount if transaction.movement_type in [MovementType.INCOME, MovementType.INVESTMENT] else -transaction.amount
                for transaction in transactions_of_day
            )
            current_balance += summed_transactions_of_day

            # Return plain dict - FastAPI will convert to Pydantic schema
            balance_points.append({
                "account_id": account_id,
                "date": date,
                "balance": current_balance
            })
        return balance_points

    def date_range_iterator(self, start_date: date, end_date: date) -> Generator[date, None, None]:
        current_date = start_date

        while current_date <= end_date:
            yield current_date
            current_date += timedelta(days=1)