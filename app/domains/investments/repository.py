from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Dict, List, Sequence, Tuple, cast
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domains.balance_points.models import BalancePoint
from app.domains.transactions.models import Transaction
from app.domains.transactions.repository import signed_amount

Movement = Tuple[date, Decimal]  # a transaction's day and signed amount


class InvestmentRepository:
    """Reads for the investment views. Callers pass only account ids they have
    already checked belong to the user."""

    def __init__(self, db: Session):
        self.db = db

    def get_points_by_account(
        self, account_ids: Sequence[UUID]
    ) -> Dict[UUID, List[BalancePoint]]:
        """Each account's balance points, oldest first: the opening, then the
        saved balances."""
        points: Dict[UUID, List[BalancePoint]] = defaultdict(list)
        for point in (
            self.db.query(BalancePoint)
            .filter(BalancePoint.account_id.in_(account_ids))
            .order_by(BalancePoint.date.asc(), BalancePoint.created_at.asc())
        ):
            points[cast(UUID, point.account_id)].append(point)
        return points

    def get_movements_by_account(
        self, account_ids: Sequence[UUID], user_id: UUID
    ) -> Dict[UUID, List[Movement]]:
        """Each account's transactions as (day, signed amount), counted like the
        account balance: ignored and deleted transactions are skipped."""
        rows = self.db.query(
            Transaction.account_id, func.date(Transaction.date), signed_amount()
        ).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.user_id == user_id,
            Transaction.is_deleted.is_(False),
            Transaction.ignored.is_(False),
        )
        movements: Dict[UUID, List[Movement]] = defaultdict(list)
        for account_id, day, amount in rows:
            movements[account_id].append((day, amount))
        return movements
