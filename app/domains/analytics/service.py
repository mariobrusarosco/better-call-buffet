from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID
from app.domains.analytics.repository import AnalyticsRepository
from app.domains.analytics.schemas import CashflowSummary, MonthlyCashflow


class AnalyticsService:
    def __init__(self, repository: AnalyticsRepository):
        self.repository = repository

    def get_cashflow_analytics(
        self,
        user_id: UUID,
        date_from: date,
        date_to: date,
        account_id: Optional[UUID] = None,
    ) -> CashflowSummary:
        """
        Orchestrates the retrieval and calculation of cashflow analytics.
        """
        monthly_data_raw = self.repository.get_monthly_cashflow(
            user_id, date_from, date_to, account_id
        )

        monthly_data = []
        total_income = Decimal(0)
        total_expenses = Decimal(0)
        total_investments = Decimal(0)

        for item in monthly_data_raw:
            income = Decimal(item["income"])
            expenses = Decimal(item["expenses"])
            investments = Decimal(item["investments"])

            # Savings = Income - Expenses
            # Note: This assumes Investments are tracked separately or are just informational in this context.
            # If investments are outflows (expenses), they might be included in expenses if movement_type='expense'
            # But if movement_type='investment', they are summed separately here.
            # The calculation `Savings = Income - Expenses` aligns with the user's example where
            # Income (10k) - Expenses (6k) = Savings (4k).
            savings = income - expenses

            monthly_data.append(
                MonthlyCashflow(
                    month=item["month"],
                    income=income,
                    expenses=expenses,
                    savings=savings,
                    investments=investments,
                )
            )

            total_income += income
            total_expenses += expenses
            total_investments += investments

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
