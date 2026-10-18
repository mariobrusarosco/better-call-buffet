"""The investment math, checked against the numbers in the spreadsheet it replaces."""

from datetime import date
from decimal import Decimal

from app.domains.investments.schemas import MonthlyBalanceSummary
from app.domains.investments.service import month_range, summarize_months, total_month

JAN, FEB, MAR = date(2023, 1, 1), date(2023, 2, 1), date(2023, 3, 1)


def d(value: str) -> Decimal:
    return Decimal(value)


def test_previdencia_first_quarter_matches_the_spreadsheet():
    points = [
        (date(2022, 12, 31), d("11036.00")),  # opening
        (date(2023, 1, 31), d("11196.00")),
        (date(2023, 2, 28), d("11451.00")),
        (date(2023, 3, 31), d("11007.00")),
    ]

    jan, feb, mar = summarize_months([JAN, FEB, MAR], points, {})

    assert (jan.started_with, jan.ended_with) == (d("11036.00"), d("11196.00"))
    assert (jan.profit, jan.profit_percentage) == (d("160.00"), d("1.45"))
    assert (feb.profit, feb.profit_percentage) == (d("255.00"), d("2.28"))
    assert (mar.profit, mar.profit_percentage) == (d("-444.00"), d("-3.88"))
    assert all(month.has_data for month in (jan, feb, mar))


def test_itau_renda_fixa_january_takes_the_income_out_of_the_profit():
    points = [
        (date(2022, 12, 31), d("251567.20")),
        (date(2023, 1, 31), d("257523.00")),
    ]

    (jan,) = summarize_months([JAN], points, {"2023-01": d("4000.00")})

    assert jan.movement == d("4000.00")
    assert jan.profit == d("1955.80")
    assert jan.profit_percentage == d("0.78")


def test_a_month_without_a_closing_has_no_profit_but_keeps_its_movement():
    points = [(date(2022, 12, 31), d("1000.00")), (date(2023, 1, 31), d("1010.00"))]

    (feb,) = summarize_months([FEB], points, {"2023-02": d("-200.00")})

    assert feb.has_data is False
    assert feb.started_with == d("1010.00")
    assert feb.ended_with is None
    assert feb.profit is None
    assert feb.movement == d("-200.00")


def test_a_skipped_month_makes_the_next_closing_start_from_the_last_one():
    points = [(date(2023, 1, 31), d("1000.00")), (date(2023, 3, 31), d("1030.00"))]

    (mar,) = summarize_months([MAR], points, {})

    assert mar.started_with == d("1000.00")
    assert mar.profit == d("30.00")


def test_a_zero_start_has_no_percentage():
    points = [(date(2022, 12, 31), d("0.00")), (date(2023, 1, 31), d("1000.00"))]

    (jan,) = summarize_months([JAN], points, {"2023-01": d("1000.00")})

    assert jan.profit == d("0.00")
    assert jan.profit_percentage is None


def row(**values) -> MonthlyBalanceSummary:
    return MonthlyBalanceSummary(month="2023-01", month_name="Jan", **values)


def test_portfolio_percentage_is_profit_over_closing_like_the_net_worth_row():
    # The spreadsheet's Net Worth for January.
    net_worth = row(
        started_with=d("581859.20"),
        ended_with=d("585635.00"),
        movement=d("-1735.00"),
        profit=d("5510.80"),
        profit_percentage=d("0.95"),
        has_data=True,
    )

    total = total_month(JAN, [net_worth])

    assert total.ended_with == d("585635.00")
    assert total.movement == d("-1735.00")
    assert total.profit == d("5510.80")
    assert total.profit_percentage == d("0.94")


def test_portfolio_totals_sum_only_accounts_with_data():
    previdencia = row(
        started_with=d("11036.00"),
        ended_with=d("11196.00"),
        profit=d("160.00"),
        has_data=True,
    )
    itau = row(
        started_with=d("251567.20"),
        ended_with=d("257523.00"),
        movement=d("4000.00"),
        profit=d("1955.80"),
        has_data=True,
    )
    no_closing_yet = row(started_with=d("500.00"), movement=d("100.00"))

    total = total_month(JAN, [previdencia, itau, no_closing_yet])

    assert total.started_with == d("262603.20")
    assert total.ended_with == d("268719.00")
    assert total.movement == d("4000.00")
    assert total.profit == d("2115.80")
    assert total.has_data is True


def test_portfolio_month_without_any_data():
    total = total_month(JAN, [row(movement=d("10.00"))])

    assert total.has_data is False
    assert total.profit is None


def test_month_range_is_inclusive_and_crosses_years():
    assert month_range(date(2022, 11, 1), date(2023, 2, 1)) == [
        date(2022, 11, 1),
        date(2022, 12, 1),
        date(2023, 1, 1),
        date(2023, 2, 1),
    ]
