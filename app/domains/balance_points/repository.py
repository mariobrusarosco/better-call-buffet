from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.domains.accounts.models import Account
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

    def get_opening_balance_point(
        self, account_id: UUID, user_id: UUID
    ) -> Optional[BalancePoint]:
        """Return the first balance point, which is the account's opening anchor."""
        return (
            self.db.query(BalancePoint)
            .join(Account, BalancePoint.account_id == Account.id)
            .filter(
                BalancePoint.account_id == account_id,
                Account.user_id == user_id,
                Account.is_deleted == False,
            )
            .order_by(BalancePoint.date.asc(), BalancePoint.created_at.asc())
            .first()
        )
