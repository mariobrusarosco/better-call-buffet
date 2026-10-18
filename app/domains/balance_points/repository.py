from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.domains.accounts.models import Account
from app.domains.balance_points.constants import TimelineStatus
from app.domains.balance_points.models import BalancePoint


class BalancePointRepository:
    """
    Repository pattern implementation for BalancePoint entity.
    Abstracts all database operations for balance point management.
    """

    def __init__(self, db: Session):
        self.db = db

    def create_balance_point(
        self, balance_point_in: dict, commit: bool = True
    ) -> BalancePoint:
        balance_point = BalancePoint(**balance_point_in)
        self.db.add(balance_point)

        if commit:
            self.db.commit()
            self.db.refresh(balance_point)
        else:
            self.db.flush()

        return balance_point

    def get_balance_points(self, account_id: UUID, user_id: UUID) -> List[BalancePoint]:
        """All of an account's balance points, oldest first. The first one is
        the account's opening anchor; any later ones are closings."""
        return (
            self.db.query(BalancePoint)
            .join(Account, BalancePoint.account_id == Account.id)
            .filter(
                BalancePoint.account_id == account_id,
                Account.user_id == user_id,
                Account.is_deleted.is_(False),
            )
            .order_by(BalancePoint.date.asc(), BalancePoint.created_at.asc())
            .all()
        )

    def get_balance_point(
        self, account_id: UUID, point_date: date
    ) -> Optional[BalancePoint]:
        return (
            self.db.query(BalancePoint)
            .filter(
                BalancePoint.account_id == account_id,
                BalancePoint.date == point_date,
            )
            .first()
        )

    def upsert_balance_point(
        self, account_id: UUID, point_date: date, balance: Decimal
    ) -> BalancePoint:
        """Set the account's balance on a date, replacing any value already
        recorded for that date (one point per account per day)."""
        balance_point = self.get_balance_point(account_id, point_date)
        if balance_point is None:
            balance_point = BalancePoint(
                account_id=account_id,
                date=point_date,
                balance=balance,
                timeline_status=TimelineStatus.CURRENT.value,
                has_transactions=False,
            )
            self.db.add(balance_point)
        else:
            self.db.query(BalancePoint).filter(
                BalancePoint.id == balance_point.id
            ).update({BalancePoint.balance: balance})

        self.db.commit()
        self.db.refresh(balance_point)
        return balance_point

    def delete_balance_point(self, balance_point: BalancePoint) -> None:
        self.db.delete(balance_point)
        self.db.commit()
