from typing import List, Dict
from uuid import UUID
from datetime import datetime
from collections import defaultdict

from sqlalchemy.orm import Session
from app.domains.balance_points.models import BalancePoint


class ReportAccountsService:
    def __init__(self, db: Session):
        self.db = db

    def get_all_accounts_balance(self, user_id: UUID) -> any:
        pass

    def get_account_monthly_balance(self, balance_points: List[BalancePoint]) -> List[Dict]:
        # Group balance points by month
        monthly_points = defaultdict(list)
        for point in balance_points:
            # Create month key in YYYY-MM format
            month_key = point.date.strftime("%Y-%m")
            monthly_points[month_key].append(point)
        
        # Get the latest balance for each month
        monthly_balances = []
        for month, points in sorted(monthly_points.items()):
            # Sort points by date to get the latest
            latest_point = max(points, key=lambda p: p.date)
            monthly_balances.append({
                "month": month,
                "balance": latest_point.balance,
                "date": latest_point.date
            })
        
        return monthly_balances
        