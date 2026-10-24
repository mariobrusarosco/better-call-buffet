from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.domains.cashflow.repository import CashflowRepository
from app.domains.cashflow.schemas import CashflowSummary, MonthlyCashflow


class CashflowService:
    def __init__(self, db: Session):
        self.repository = CashflowRepository(db)

    def get_monthly_cashflow(
        self,
        user_id: UUID,
        date_from: date,
        date_to: date,
        account_id: Optional[UUID] = None,
    ) -> CashflowSummary:
        """
        Income, expenses and savings per month, plus totals for the period.
        """
        monthly_data_raw = self.repository.get_monthly_cashflow(
            user_id, date_from, date_to, account_id
        )

        monthly_data = []
        total_income = Decimal(0)
        total_expenses = Decimal(0)

        for item in monthly_data_raw:
            income = Decimal(item["income"])
            expenses = Decimal(item["expenses"])

            # Savings = Income - Expenses, e.g. 10k - 6k = 4k.
            savings = income - expenses

            monthly_data.append(
                MonthlyCashflow(
                    month=item["month"],
                    income=income,
                    expenses=expenses,
                    savings=savings,
                )
            )

            total_income += income
            total_expenses += expenses

        # Net cashflow over the entire period
        net_cashflow = total_income - total_expenses

        # Savings Rate = (Net Cashflow / Total Income) * 100
        savings_rate = 0.0
        if total_income > 0:
            savings_rate = (float(net_cashflow) / float(total_income)) * 100

        return CashflowSummary(
            total_income=total_income,
            total_expenses=total_expenses,
            net_cashflow=net_cashflow,
            savings_rate=round(savings_rate, 2),
            monthly_data=monthly_data,
        )
