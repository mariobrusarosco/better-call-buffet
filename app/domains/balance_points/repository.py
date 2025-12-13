from sqlalchemy.orm import Session
from app.domains.balance_points.models import BalancePoint

class BalancePointRepository:
    """
    Repository pattern implementation for BalancePoint entity.
    Abstracts all database operations for balance point management.
    """
    def __init__(self, db: Session):
        self.db = db

    def create_balance_point(self, balance_point_in: dict) -> BalancePoint:
        # Instance
        balance_point = BalancePoint(**balance_point_in)
        # Add
        self.db.add(balance_point)
        # Commit
        self.db.commit()
        # Refresh
        self.db.refresh(balance_point)
        # Return
        return balance_point