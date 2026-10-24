from decimal import Decimal


def test_monthly_cashflow_uses_the_cashflow_scope(ledger):
    response = ledger.client.get("/api/v1/cashflow", params=ledger.period)

    assert response.status_code == 200
    body = response.json()
    # Ignored, deleted and last-year rows excluded, like the views.
    assert Decimal(body["total_expenses"]) == Decimal("4480.00")
    assert Decimal(body["total_income"]) == Decimal("20.00")
    assert set(body["monthly_data"][0]) == {"month", "income", "expenses", "savings"}
