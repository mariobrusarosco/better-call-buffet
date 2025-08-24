from datetime import date, datetime, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

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

    def get_by_account_and_user(
        self, account_id: UUID, user_id: UUID
    ) -> List[BalancePoint]:
        """Get all balance points for a specific account and user"""
        return (
            self.db.query(BalancePoint)
            .filter(
                BalancePoint.account_id == account_id, BalancePoint.user_id == user_id
            )
            .order_by(BalancePoint.date.desc())
            .all()
        )

    def get_by_id_and_user(
        self, balance_point_id: UUID, user_id: UUID
    ) -> Optional[BalancePoint]:
        """Get a specific balance point by ID and user"""
        return (
            self.db.query(BalancePoint)
            .filter(
                BalancePoint.id == balance_point_id, BalancePoint.user_id == user_id
            )
            .first()
        )

    def get_by_user_and_date_range(
        self, user_id: UUID, start_date: datetime, end_date: datetime
    ) -> List[BalancePoint]:
        """Get balance points for a user within a date range"""
        return (
            self.db.query(BalancePoint)
            .filter(
                BalancePoint.user_id == user_id,
                BalancePoint.date >= start_date,
                BalancePoint.date <= end_date,
            )
            .order_by(BalancePoint.date.desc())
            .all()
        )

    def get_latest_by_account(
        self, account_id: UUID, user_id: UUID
    ) -> Optional[BalancePoint]:
        """Get the most recent balance point for an account"""
        return (
            self.db.query(BalancePoint)
            .filter(
                BalancePoint.account_id == account_id, BalancePoint.user_id == user_id
            )
            .order_by(BalancePoint.date.desc())
            .first()
        )

    def get_by_account_and_date(
        self, account_id: UUID, user_id: UUID, target_date: date
    ) -> Optional[BalancePoint]:
        """Get balance point for a specific account on a specific date"""
        return (
            self.db.query(BalancePoint)
            .filter(
                BalancePoint.account_id == account_id,
                BalancePoint.user_id == user_id,
                func.date(BalancePoint.date) == target_date,
            )
            .first()
        )

    def get_balance_history_summary(
        self, user_id: UUID, account_id: Optional[UUID] = None
    ) -> List[dict]:
        """Get balance history with calculated movements (differences between consecutive points)"""
        query = self.db.query(BalancePoint).filter(BalancePoint.user_id == user_id)

        if account_id:
            query = query.filter(BalancePoint.account_id == account_id)

        balance_points = query.order_by(
            BalancePoint.account_id, BalancePoint.date
        ).all()

        # Calculate movements between consecutive balance points
        result = []
        prev_balance_by_account = {}

        for bp in balance_points:
            movement = 0.0
            if bp.account_id in prev_balance_by_account:
                movement = bp.balance - prev_balance_by_account[bp.account_id]

            result.append(
                {
                    "id": bp.id,
                    "account_id": bp.account_id,
                    "date": bp.date,
                    "balance": bp.balance,
                    "movement": movement,
                    "note": bp.note,
                }
            )

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

    def exists_for_account_and_date(
        self, account_id: UUID, user_id: UUID, target_date: date
    ) -> bool:
        """Check if a balance point exists for an account on a specific date"""
        return (
            self.db.query(BalancePoint)
            .filter(
                BalancePoint.account_id == account_id,
                BalancePoint.user_id == user_id,
                func.date(BalancePoint.date) == target_date,
            )
            .first()
            is not None
        )

    def get_account_balance_trend(
        self, account_id: UUID, user_id: UUID, days: int = 30
    ) -> List[BalancePoint]:
        """Get balance points for an account over the last N days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return (
            self.db.query(BalancePoint)
            .filter(
                BalancePoint.account_id == account_id,
                BalancePoint.user_id == user_id,
                BalancePoint.date >= cutoff_date,
            )
            .order_by(BalancePoint.date.asc())
            .all()
        )

    def get_monthly_summaries(
        self, account_id: UUID, user_id: UUID, year: int = None, months: int = 12
    ) -> List[dict]:
        """Get monthly balance summaries for an account"""
        from datetime import datetime
        from calendar import month_name
        
        if year is None:
            year = datetime.utcnow().year
        
        # Get all balance points for the account in the specified year
        balance_points = (
            self.db.query(BalancePoint)
            .filter(
                BalancePoint.account_id == account_id,
                BalancePoint.user_id == user_id,
                func.extract('year', BalancePoint.date) == year
            )
            .order_by(BalancePoint.date)
            .all()
        )
        
        # Group balance points by month
        monthly_data = {}
        for bp in balance_points:
            month_key = bp.date.strftime('%Y-%m')
            if month_key not in monthly_data:
                monthly_data[month_key] = []
            monthly_data[month_key].append(bp)
        
        # Calculate summaries for each month
        summaries = []
        previous_month_end = None
        
        for month_num in range(1, min(months + 1, 13)):
            month_key = f"{year}-{month_num:02d}"
            month_points = monthly_data.get(month_key, [])
            
            summary = {
                "month": month_key,
                "month_name": month_name[month_num][:3],  # Short month name
                "started_with": None,
                "ended_with": None,
                "movement": 0.0,
                "profit": 0.0,
                "profit_percentage": 0.0,
                "has_data": False
            }
            
            if month_points:
                # Sort by date to ensure correct first/last
                month_points.sort(key=lambda x: x.date)
                
                summary["started_with"] = float(month_points[0].balance)
                summary["ended_with"] = float(month_points[-1].balance)
                summary["movement"] = summary["ended_with"] - summary["started_with"]
                
                # Calculate profit: current_month_started - previous_month_ended
                if previous_month_end is not None:
                    summary["profit"] = summary["started_with"] - previous_month_end
                    if previous_month_end != 0:
                        summary["profit_percentage"] = (summary["profit"] / previous_month_end) * 100
                else:
                    # First month with data - no previous month to compare
                    summary["profit"] = 0.0
                    summary["profit_percentage"] = 0.0
                
                summary["has_data"] = True
                previous_month_end = summary["ended_with"]  # Store for next iteration
            
            summaries.append(summary)
        
        return summaries

    def upsert(
        self, account_id: UUID, user_id: UUID, target_date: date, balance_data: dict
    ) -> BalancePoint:
        """
        Create or update a balance point for a specific account and date.
        If a balance point exists for this date, it will be updated.
        If not, a new one will be created.
        """
        # Check if balance point exists for this account and date
        existing = (
            self.db.query(BalancePoint)
            .filter(
                BalancePoint.account_id == account_id,
                BalancePoint.user_id == user_id,
                func.date(BalancePoint.date) == target_date,
            )
            .first()
        )
        
        if existing:
            # Update existing balance point
            for key, value in balance_data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            # Create new balance point
            new_balance_point = BalancePoint(
                account_id=account_id,
                user_id=user_id,
                date=target_date,
                **balance_data
            )
            self.db.add(new_balance_point)
            self.db.commit()
            self.db.refresh(new_balance_point)
            return new_balance_point

    def get_total_balance_at_date(self, user_id: UUID, target_date: date) -> float:
        """Calculate total balance across all accounts at a specific date"""
        # Get the latest balance point for each account up to the target date
        latest_points = []

        # Get all unique account IDs for the user
        account_ids = (
            self.db.query(BalancePoint.account_id)
            .filter(BalancePoint.user_id == user_id)
            .distinct()
            .all()
        )

        total_balance = 0.0
        for (account_id,) in account_ids:
            latest_point = (
                self.db.query(BalancePoint)
                .filter(
                    BalancePoint.account_id == account_id,
                    BalancePoint.user_id == user_id,
                    func.date(BalancePoint.date) <= target_date,
                )
                .order_by(BalancePoint.date.desc())
                .first()
            )

            if latest_point:
                total_balance += latest_point.balance

        return total_balance
