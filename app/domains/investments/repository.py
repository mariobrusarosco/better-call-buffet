from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Dict, List, Sequence, Tuple
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domains.balance_points.models import BalancePoint
from app.domains.transactions.models import Transaction
from app.domains.transactions.repository import signed_amount

Points = List[Tuple[date, Decimal]]
Movements = Dict[str, Decimal]  # "YYYY-MM" -> signed total


class InvestmentRepository:
    """Reads for the investment views. Callers pass only account ids they have
    already checked belong to the user."""

    def __init__(self, db: Session):
        self.db = db

    def get_points_by_account(self, account_ids: Sequence[UUID]) -> Dict[UUID, Points]:
        """Each account's balance points (opening first, then closings), oldest
        first, in one query."""
        rows = (
            self.db.query(
                BalancePoint.account_id, BalancePoint.date, BalancePoint.balance
            )
            .filter(BalancePoint.account_id.in_(account_ids))
            .order_by(BalancePoint.date.asc(), BalancePoint.created_at.asc())
            .all()
        )
        points: Dict[UUID, Points] = defaultdict(list)
        for account_id, point_date, balance in rows:
            points[account_id].append((point_date, balance))
        return points

    def get_movements_by_account(
        self,
        account_ids: Sequence[UUID],
        user_id: UUID,
        date_from: date,
        date_to: date,
    ) -> Dict[UUID, Movements]:
        """Signed transaction totals per account per month, for transactions
        dated on or after `date_from` and before `date_to`. Same counting rule
        as the account balance: ignored and deleted transactions are skipped."""
        month = func.to_char(Transaction.date, "YYYY-MM")
        rows = (
            self.db.query(Transaction.account_id, month, func.sum(signed_amount()))
            .filter(
                Transaction.account_id.in_(account_ids),
                Transaction.user_id == user_id,
                Transaction.is_deleted.is_(False),
                Transaction.ignored.is_(False),
                Transaction.date >= date_from,
                Transaction.date < date_to,
            )
            .group_by(Transaction.account_id, month)
            .all()
        )
        movements: Dict[UUID, Movements] = defaultdict(dict)
        for account_id, month_key, total in rows:
            movements[account_id][month_key] = total
        return movements
