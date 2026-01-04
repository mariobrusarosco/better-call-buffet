from datetime import date
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from app.domains.transactions.models import Transaction


class AnalyticsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_monthly_cashflow(
        self,
        user_id: UUID,
        date_from: date,
        date_to: date,
        account_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        """
        Aggregates transaction data by month to calculate income, expenses, and investments.
        """
        # Truncate date to month: TO_CHAR(date, 'YYYY-MM')
        month_col = func.to_char(Transaction.date, "YYYY-MM").label("month")

        # Aggregations
        income_sum = func.sum(
            case((Transaction.movement_type == "income", Transaction.amount), else_=0)
        ).label("income")

        expense_sum = func.sum(
            case((Transaction.movement_type == "expense", Transaction.amount), else_=0)
        ).label("expenses")

        investment_sum = func.sum(
            case(
                (Transaction.movement_type == "investment", Transaction.amount), else_=0
            )
        ).label("investments")

        query = self.db.query(
            month_col, income_sum, expense_sum, investment_sum
        ).filter(
            Transaction.user_id == user_id,
            Transaction.date >= date_from,
            Transaction.date <= date_to,
            Transaction.is_deleted == False,
            Transaction.ignored == False,
        )

        if account_id:
            query = query.filter(Transaction.account_id == account_id)

        results = query.group_by(month_col).order_by(month_col).all()

        # Format results as dicts
        return [
            {
                "month": r.month,
                "income": r.income or 0,
                "expenses": r.expenses or 0,
                "investments": r.investments or 0,
            }
            for r in results
        ]
