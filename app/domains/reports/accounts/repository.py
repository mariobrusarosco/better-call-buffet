from typing import List, Dict, Any, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, extract
from uuid import UUID
from collections import defaultdict

from app.domains.accounts.models import Account
from app.domains.balance_points.models import BalancePoint
from app.domains.accounts.schemas import AccountType


class ReportsAccountsRepository:
    """
    Repository pattern implementation for Account Reports.
    Specializes in aggregation and analytics queries for financial reporting.
    """
    
    def __init__(self, db: Session):
        self.db = db

    def get_accounts_with_balance_history(
        self, 
        user_id: UUID, 
        account_type: AccountType,
        start_date: datetime,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get accounts with their balance point history for a specific type and date range.
        """
        # Build the query for accounts
        accounts_query = self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.type == account_type,
            Account.is_active == True
        )
        
        accounts = accounts_query.all()
        
        result = []
        for account in accounts:
            # Get balance points for this account within date range
            balance_query = self.db.query(BalancePoint).filter(
                BalancePoint.account_id == account.id,
                BalancePoint.user_id == user_id,
                BalancePoint.date >= start_date
            )
            
            if end_date:
                balance_query = balance_query.filter(BalancePoint.date <= end_date)
            
            balance_points = balance_query.order_by(BalancePoint.date).all()
            
            if balance_points:
                result.append({
                    "account_id": account.id,
                    "account_name": account.name,
                    "account_type": account.type,
                    "balance_points": balance_points
                })
        
        return result

    def get_monthly_balance_summary(
        self, 
        user_id: UUID, 
        account_type: AccountType,
        start_date: datetime,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get monthly balance summaries grouped by account and month.
        """
        accounts_data = self.get_accounts_with_balance_history(
            user_id, account_type, start_date, end_date
        )
        
        result = {
            "type": account_type,
            "start_date": start_date.date(),
            "end_date": end_date.date() if end_date else None,
            "accounts": []
        }
        
        for account_data in accounts_data:
            monthly_balances = self._calculate_monthly_balances(account_data["balance_points"])
            
            result["accounts"].append({
                "account_id": account_data["account_id"],
                "account_name": account_data["account_name"],
                "monthly_balances": monthly_balances
            })
        
        return result

    def get_balance_trends_by_account_type(
        self, 
        user_id: UUID, 
        start_date: datetime,
        end_date: Optional[datetime] = None
    ) -> Dict[str, List[Dict]]:
        """
        Get balance trends grouped by account type.
        """
        # Query all balance points with account information
        query = self.db.query(BalancePoint, Account).join(
            Account, BalancePoint.account_id == Account.id
        ).filter(
            BalancePoint.user_id == user_id,
            Account.user_id == user_id,
            Account.is_active == True,
            BalancePoint.date >= start_date
        )
        
        if end_date:
            query = query.filter(BalancePoint.date <= end_date)
        
        results = query.order_by(Account.type, BalancePoint.date).all()
        
        # Group by account type
        trends_by_type = defaultdict(list)
        for balance_point, account in results:
            trends_by_type[account.type].append({
                "account_id": account.id,
                "account_name": account.name,
                "date": balance_point.date,
                "balance": balance_point.balance,
                "note": balance_point.note
            })
        
        return dict(trends_by_type)

    def get_total_balance_by_type_and_month(
        self, 
        user_id: UUID,
        start_date: datetime,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get total balance by account type and month.
        """
        # Query balance points with account type information
        query = self.db.query(
            Account.type,
            func.date_trunc('month', BalancePoint.date).label('month'),
            func.max(BalancePoint.date).label('latest_date_in_month'),
            func.sum(BalancePoint.balance).label('total_balance')
        ).join(
            Account, BalancePoint.account_id == Account.id
        ).filter(
            BalancePoint.user_id == user_id,
            Account.user_id == user_id,
            Account.is_active == True,
            BalancePoint.date >= start_date
        )
        
        if end_date:
            query = query.filter(BalancePoint.date <= end_date)
        
        results = query.group_by(
            Account.type,
            func.date_trunc('month', BalancePoint.date)
        ).order_by(
            Account.type,
            func.date_trunc('month', BalancePoint.date)
        ).all()
        
        return [
            {
                "account_type": result.type,
                "month": result.month.date(),
                "total_balance": float(result.total_balance or 0),
                "latest_date_in_month": result.latest_date_in_month.date()
            }
            for result in results
        ]

    def get_account_performance_metrics(
        self, 
        user_id: UUID,
        account_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get performance metrics for accounts (growth, volatility, etc.).
        """
        query = self.db.query(BalancePoint).filter(
            BalancePoint.user_id == user_id
        )
        
        if account_id:
            query = query.filter(BalancePoint.account_id == account_id)
        
        if start_date:
            query = query.filter(BalancePoint.date >= start_date)
        
        if end_date:
            query = query.filter(BalancePoint.date <= end_date)
        
        balance_points = query.order_by(BalancePoint.date).all()
        
        if not balance_points:
            return {"error": "No balance points found for the specified criteria"}
        
        # Calculate metrics
        balances = [bp.balance for bp in balance_points]
        start_balance = balances[0]
        end_balance = balances[-1]
        
        total_growth = end_balance - start_balance
        growth_percentage = (total_growth / start_balance) * 100 if start_balance != 0 else 0
        
        # Calculate volatility (standard deviation)
        avg_balance = sum(balances) / len(balances)
        variance = sum((b - avg_balance) ** 2 for b in balances) / len(balances)
        volatility = variance ** 0.5
        
        return {
            "total_data_points": len(balance_points),
            "start_balance": start_balance,
            "end_balance": end_balance,
            "total_growth": total_growth,
            "growth_percentage": round(growth_percentage, 2),
            "average_balance": round(avg_balance, 2),
            "volatility": round(volatility, 2),
            "min_balance": min(balances),
            "max_balance": max(balances),
            "date_range": {
                "start": balance_points[0].date.date(),
                "end": balance_points[-1].date.date()
            }
        }

    def _calculate_monthly_balances(self, balance_points: List[BalancePoint]) -> List[Dict]:
        """
        Helper method to calculate monthly balances from balance points.
        """
        # Group balance points by month
        monthly_points = defaultdict(list)
        for point in balance_points:
            month_key = point.date.strftime("%Y-%m")
            monthly_points[month_key].append(point)
        
        # Get the latest balance for each month
        monthly_balances = []
        for month, points in sorted(monthly_points.items()):
            latest_point = max(points, key=lambda p: p.date)
            monthly_balances.append({
                "month": month,
                "balance": latest_point.balance,
                "date": latest_point.date,
                "note": latest_point.note
            })
        
        return monthly_balances 