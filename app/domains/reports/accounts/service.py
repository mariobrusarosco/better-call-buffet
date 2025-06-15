from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy.orm import Session
from app.domains.reports.accounts.repository import ReportsAccountsRepository
from app.domains.accounts.schemas import AccountType
from app.domains.accounts.service import AccountService


class ReportAccountsService:
    """
    Service layer for Account Reports business logic.
    Uses ReportsAccountsRepository for analytics and aggregation operations.
    """
    
    def __init__(self, db: Session):
        self.repository = ReportsAccountsRepository(db)
        self.account_service = AccountService(db)

    def get_account_balance_report(
        self, 
        user_id: UUID, 
        account_type: AccountType,
        start_date: datetime,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive account balance report.
        
        Args:
            user_id: ID of the user
            account_type: Type of accounts to include in report
            start_date: Start date for the report
            end_date: End date for the report (optional)
            
        Returns:
            Comprehensive balance report with monthly summaries
        """
        # Validate that user has accounts of this type
        user_accounts = self.account_service.get_accounts_by_type(user_id, account_type)
        if not user_accounts:
            return {
                "type": account_type,
                "start_date": start_date.date(),
                "end_date": end_date.date() if end_date else None,
                "accounts": [],
                "message": f"No {account_type} accounts found for user"
            }
        
        return self.repository.get_monthly_balance_summary(
            user_id, account_type, start_date, end_date
        )

    def get_balance_trends_across_types(
        self, 
        user_id: UUID,
        start_date: datetime,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get balance trends across all account types.
        
        Args:
            user_id: ID of the user
            start_date: Start date for analysis
            end_date: End date for analysis (optional)
            
        Returns:
            Balance trends grouped by account type
        """
        trends = self.repository.get_balance_trends_by_account_type(
            user_id, start_date, end_date
        )
        
        return {
            "start_date": start_date.date(),
            "end_date": end_date.date() if end_date else None,
            "trends_by_type": trends,
            "summary": {
                "account_types_analyzed": len(trends),
                "total_data_points": sum(len(points) for points in trends.values())
            }
        }

    def get_monthly_totals_by_type(
        self, 
        user_id: UUID,
        start_date: datetime,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get monthly totals grouped by account type.
        
        Args:
            user_id: ID of the user
            start_date: Start date for analysis
            end_date: End date for analysis (optional)
            
        Returns:
            Monthly totals by account type
        """
        monthly_data = self.repository.get_total_balance_by_type_and_month(
            user_id, start_date, end_date
        )
        
        # Group by account type for easier consumption
        grouped_data = {}
        for item in monthly_data:
            account_type = item["account_type"]
            if account_type not in grouped_data:
                grouped_data[account_type] = []
            grouped_data[account_type].append({
                "month": item["month"],
                "total_balance": item["total_balance"],
                "latest_date_in_month": item["latest_date_in_month"]
            })
        
        return {
            "start_date": start_date.date(),
            "end_date": end_date.date() if end_date else None,
            "monthly_totals_by_type": grouped_data,
            "summary": {
                "account_types": list(grouped_data.keys()),
                "total_months_analyzed": len(monthly_data)
            }
        }

    def get_account_performance_analysis(
        self, 
        user_id: UUID,
        account_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get detailed performance analysis for accounts.
        
        Args:
            user_id: ID of the user
            account_id: Specific account ID (optional, if None analyzes all accounts)
            start_date: Start date for analysis (optional)
            end_date: End date for analysis (optional)
            
        Returns:
            Performance metrics including growth, volatility, etc.
        """
        # Validate account ownership if specific account is requested
        if account_id:
            account = self.account_service.get_account_by_id(account_id, user_id)
            if not account:
                raise ValueError("Account not found or does not belong to user")
        
        metrics = self.repository.get_account_performance_metrics(
            user_id, account_id, start_date, end_date
        )
        
        # Add interpretation of metrics
        if "error" not in metrics:
            metrics["interpretation"] = self._interpret_performance_metrics(metrics)
        
        return metrics

    def get_portfolio_overview(
        self, 
        user_id: UUID,
        start_date: datetime,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get a comprehensive portfolio overview combining multiple metrics.
        
        Args:
            user_id: ID of the user
            start_date: Start date for analysis
            end_date: End date for analysis (optional)
            
        Returns:
            Comprehensive portfolio overview
        """
        # Get trends across all types
        trends = self.get_balance_trends_across_types(user_id, start_date, end_date)
        
        # Get monthly totals
        monthly_totals = self.get_monthly_totals_by_type(user_id, start_date, end_date)
        
        # Get overall performance metrics
        performance = self.get_account_performance_analysis(user_id, None, start_date, end_date)
        
        # Calculate portfolio diversity metrics
        diversity_metrics = self._calculate_portfolio_diversity(trends["trends_by_type"])
        
        return {
            "period": {
                "start_date": start_date.date(),
                "end_date": end_date.date() if end_date else None
            },
            "trends_by_type": trends["trends_by_type"],
            "monthly_totals": monthly_totals["monthly_totals_by_type"],
            "performance_metrics": performance,
            "diversity_metrics": diversity_metrics,
            "summary": {
                "total_account_types": len(trends["trends_by_type"]),
                "total_data_points": trends["summary"]["total_data_points"],
                "analysis_period_days": (
                    (end_date or datetime.utcnow()) - start_date
                ).days
            }
        }

    def get_account_monthly_balance(self, balance_points) -> List[Dict]:
        """
        Legacy method for backward compatibility.
        Calculate monthly balances from balance points.
        """
        return self.repository._calculate_monthly_balances(balance_points)

    def _interpret_performance_metrics(self, metrics: Dict[str, Any]) -> Dict[str, str]:
        """
        Provide human-readable interpretation of performance metrics.
        """
        growth_percentage = metrics.get("growth_percentage", 0)
        volatility = metrics.get("volatility", 0)
        
        interpretations = {}
        
        # Growth interpretation
        if growth_percentage > 10:
            interpretations["growth"] = "Strong positive growth"
        elif growth_percentage > 0:
            interpretations["growth"] = "Moderate positive growth"
        elif growth_percentage == 0:
            interpretations["growth"] = "No growth"
        else:
            interpretations["growth"] = "Negative growth (decline)"
        
        # Volatility interpretation
        avg_balance = metrics.get("average_balance", 0)
        volatility_percentage = (volatility / avg_balance) * 100 if avg_balance > 0 else 0
        
        if volatility_percentage < 5:
            interpretations["volatility"] = "Low volatility (stable)"
        elif volatility_percentage < 15:
            interpretations["volatility"] = "Moderate volatility"
        else:
            interpretations["volatility"] = "High volatility (unstable)"
        
        return interpretations

    def _calculate_portfolio_diversity(self, trends_by_type: Dict[str, List]) -> Dict[str, Any]:
        """
        Calculate portfolio diversity metrics.
        """
        total_accounts = sum(len(set(item["account_id"] for item in trend_data)) 
                           for trend_data in trends_by_type.values())
        
        account_type_distribution = {
            account_type: len(set(item["account_id"] for item in trend_data))
            for account_type, trend_data in trends_by_type.items()
        }
        
        return {
            "total_accounts": total_accounts,
            "account_types_count": len(trends_by_type),
            "account_type_distribution": account_type_distribution,
            "diversity_score": len(trends_by_type) / max(total_accounts, 1)  # Simple diversity score
        }
        