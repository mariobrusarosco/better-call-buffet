from typing import List, Optional
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from uuid import UUID

from app.domains.balance_points.models import BalancePoint


class BalancePointRepository:
    """
    Repository pattern implementation for BalancePoint entity.
    Abstracts all database operations for balance point management.
    """
    
    def __init__(self, db: Session):
        self.db = db

    def create(self, balance_point_data: dict) -> BalancePoint:
        """Create a new balance point"""
        db_balance_point = BalancePoint(**balance_point_data)
        self.db.add(db_balance_point)
        self.db.commit()
        self.db.refresh(db_balance_point)
        return db_balance_point

    def get_by_account_and_user(self, account_id: UUID, user_id: UUID) -> List[BalancePoint]:
        """Get all balance points for a specific account and user"""
        return self.db.query(BalancePoint).filter(
            BalancePoint.account_id == account_id,
            BalancePoint.user_id == user_id
        ).order_by(BalancePoint.date.desc()).all()

    def get_by_id_and_user(self, balance_point_id: UUID, user_id: UUID) -> Optional[BalancePoint]:
        """Get a specific balance point by ID and user"""
        return self.db.query(BalancePoint).filter(
            BalancePoint.id == balance_point_id,
            BalancePoint.user_id == user_id
        ).first()

    def get_by_user_and_date_range(self, user_id: UUID, start_date: datetime, end_date: datetime) -> List[BalancePoint]:
        """Get balance points for a user within a date range"""
        return self.db.query(BalancePoint).filter(
            BalancePoint.user_id == user_id,
            BalancePoint.date >= start_date,
            BalancePoint.date <= end_date
        ).order_by(BalancePoint.date.desc()).all()

    def get_latest_by_account(self, account_id: UUID, user_id: UUID) -> Optional[BalancePoint]:
        """Get the most recent balance point for an account"""
        return self.db.query(BalancePoint).filter(
            BalancePoint.account_id == account_id,
            BalancePoint.user_id == user_id
        ).order_by(BalancePoint.date.desc()).first()

    def get_by_account_and_date(self, account_id: UUID, user_id: UUID, target_date: date) -> Optional[BalancePoint]:
        """Get balance point for a specific account on a specific date"""
        return self.db.query(BalancePoint).filter(
            BalancePoint.account_id == account_id,
            BalancePoint.user_id == user_id,
            func.date(BalancePoint.date) == target_date
        ).first()

    def get_balance_history_summary(self, user_id: UUID, account_id: Optional[UUID] = None) -> List[dict]:
        """Get balance history with calculated movements (differences between consecutive points)"""
        query = self.db.query(BalancePoint).filter(BalancePoint.user_id == user_id)
        
        if account_id:
            query = query.filter(BalancePoint.account_id == account_id)
        
        balance_points = query.order_by(BalancePoint.account_id, BalancePoint.date).all()
        
        # Calculate movements between consecutive balance points
        result = []
        prev_balance_by_account = {}
        
        for bp in balance_points:
            movement = 0.0
            if bp.account_id in prev_balance_by_account:
                movement = bp.balance - prev_balance_by_account[bp.account_id]
            
            result.append({
                'id': bp.id,
                'account_id': bp.account_id,
                'date': bp.date,
                'balance': bp.balance,
                'movement': movement,
                'note': bp.note
            })
            
            prev_balance_by_account[bp.account_id] = bp.balance
            
        return result

    def update(self, balance_point: BalancePoint, update_data: dict) -> BalancePoint:
        """Update an existing balance point"""
        for key, value in update_data.items():
            if hasattr(balance_point, key):
                setattr(balance_point, key, value)
        
        self.db.commit()
        self.db.refresh(balance_point)
        return balance_point

    def delete(self, balance_point: BalancePoint) -> None:
        """Delete a balance point"""
        self.db.delete(balance_point)
        self.db.commit()

    def exists_for_account_and_date(self, account_id: UUID, user_id: UUID, target_date: date) -> bool:
        """Check if a balance point exists for an account on a specific date"""
        return self.db.query(BalancePoint).filter(
            BalancePoint.account_id == account_id,
            BalancePoint.user_id == user_id,
            func.date(BalancePoint.date) == target_date
        ).first() is not None

    def get_account_balance_trend(self, account_id: UUID, user_id: UUID, days: int = 30) -> List[BalancePoint]:
        """Get balance points for an account over the last N days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return self.db.query(BalancePoint).filter(
            BalancePoint.account_id == account_id,
            BalancePoint.user_id == user_id,
            BalancePoint.date >= cutoff_date
        ).order_by(BalancePoint.date.asc()).all()

    def get_total_balance_at_date(self, user_id: UUID, target_date: date) -> float:
        """Calculate total balance across all accounts at a specific date"""
        # Get the latest balance point for each account up to the target date
        latest_points = []
        
        # Get all unique account IDs for the user
        account_ids = self.db.query(BalancePoint.account_id).filter(
            BalancePoint.user_id == user_id
        ).distinct().all()
        
        total_balance = 0.0
        for (account_id,) in account_ids:
            latest_point = self.db.query(BalancePoint).filter(
                BalancePoint.account_id == account_id,
                BalancePoint.user_id == user_id,
                func.date(BalancePoint.date) <= target_date
            ).order_by(BalancePoint.date.desc()).first()
            
            if latest_point:
                total_balance += latest_point.balance
                
        return total_balance 