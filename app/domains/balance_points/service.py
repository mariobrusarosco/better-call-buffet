from typing import List, Optional
from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session

from app.domains.balance_points.models import BalancePoint
from app.domains.balance_points.schemas import BalancePointIn
from app.domains.accounts.service import AccountService

class BalancePointService:
    def __init__(self, db: Session):
        self.db = db
        self.account_service = AccountService(db)

    def create_balance_point(self, balance_point_in: BalancePointIn, user_id: UUID) -> BalancePoint:
        # Verify the account exists and belongs to the user
        account = self.account_service.get_account_by_id(balance_point_in.account_id)
        if account.user_id != user_id:
            raise ValueError("Account does not belong to the user")
        
        db_balance_point = BalancePoint(
            user_id=user_id,
            account_id=balance_point_in.account_id,
            date=balance_point_in.date or datetime.utcnow(),
            balance=balance_point_in.balance,
            note=balance_point_in.note
        )
        
        self.db.add(db_balance_point)
        self.db.commit()
        self.db.refresh(db_balance_point)
        return db_balance_point
