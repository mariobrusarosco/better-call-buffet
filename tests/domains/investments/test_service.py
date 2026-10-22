"""The investment math, checked against the numbers in the spreadsheet it replaces."""

from datetime import date
from decimal import Decimal

from app.domains.investments.service import (
    MonthGrowth,
    Point,
    balance_at_end_of,
    chained_percentage,
    compare_with_previous,
    growth_by_month,
    invested_during,
    summarize_month,
    total_invested,
)


def d(value: str) -> Decimal:
    return Decimal(value)


PREVIDENCIA = [
    Point(date(2022, 12, 31), d("11036.00")),  # opening
    Point(date(2023, 1, 31), d("11196.00")),
    Point(date(2023, 2, 28), d("11451.00")),
    Point(date(2023, 3, 31), d("11007.00")),
]


def test_previdencia_first_quarter_matches_the_spreadsheet():
    jan, feb, mar = (summarize_month(2023, m, PREVIDENCIA, []) for m in (1, 2, 3))

    assert (jan.month, jan.year, jan.month_name) == (1, 2023, "Jan")
    assert (jan.started_with, jan.ended_with) == (d("11036.00"), d("11196.00"))
    assert (jan.profit, jan.profit_percentage) == (d("160.00"), 1.45)
    assert (feb.profit, feb.profit_percentage) == (d("255.00"), 2.28)
    assert (mar.profit, mar.profit_percentage) == (d("-444.00"), -3.88)
    assert all(month.has_data for month in (jan, feb, mar))


def test_itau_renda_fixa_january_takes_the_income_out_of_the_profit():
    points = [
        Point(date(2022, 12, 31), d("251567.20")),
        Point(date(2023, 1, 31), d("257523.00")),
    ]

    jan = summarize_month(2023, 1, points, [(date(2023, 1, 15), d("4000.00"))])

    assert jan.movement == d("4000.00")
    assert jan.profit == d("1955.80")
    assert jan.profit_percentage == 0.78


def test_income_on_a_closing_day_is_inside_that_closing():
    points = [
        Point(date(2022, 12, 31), d("900.00")),  # opening
        Point(date(2023, 1, 31), d("1000.00")),
        Point(date(2023, 2, 28), d("1500.00")),
    ]
    movements = [
        (date(2023, 1, 31), d("100.00")),  # already in January's closing
        (date(2023, 2, 28), d("400.00")),  # inside February's closing
    ]

    feb = summarize_month(2023, 2, points, movements)

    assert feb.movement == d("400.00")
    assert feb.profit == d("100.00")


def test_income_on_the_opening_day_comes_after_the_opening():
    points = [
        Point(date(2022, 12, 31), d("1000.00")),
        Point(date(2023, 1, 31), d("1510.00")),
    ]

    jan = summarize_month(2023, 1, points, [(date(2022, 12, 31), d("500.00"))])

    assert jan.movement == d("500.00")
    assert jan.profit == d("10.00")


def test_a_month_without_a_balance_has_no_profit_but_keeps_its_movement():
    feb = summarize_month(
        2023,
        2,
        [
            Point(date(2022, 12, 31), d("1000.00")),
            Point(date(2023, 1, 31), d("1010.00")),
        ],
        [(date(2023, 2, 10), d("-200.00"))],
    )

    assert feb.has_data is False
    assert feb.started_with == d("1010.00")
    assert feb.ended_with is None
    assert feb.profit is None
    assert feb.movement == d("-200.00")


def test_a_skipped_month_makes_the_next_month_start_from_the_last_balance():
    points = [
        Point(date(2023, 1, 31), d("1000.00")),
        Point(date(2023, 3, 31), d("1030.00")),
    ]

    mar = summarize_month(2023, 3, points, [])

    assert mar.started_with == d("1000.00")
    assert mar.profit == d("30.00")


def test_a_zero_start_has_a_zero_percentage():
    points = [
        Point(date(2022, 12, 31), d("0.00")),
        Point(date(2023, 1, 31), d("1000.00")),
    ]

    jan = summarize_month(2023, 1, points, [(date(2023, 1, 5), d("1000.00"))])

    assert jan.profit == d("0.00")
    assert jan.profit_percentage == 0.0


def test_compare_with_previous_gives_the_spreadsheet_diff_columns():
    movement, diff, diff_percentage = compare_with_previous(PREVIDENCIA, 2, [])

    assert movement == d("0.00")
    assert diff == d("255.00")
    assert diff_percentage == 2.28


def test_total_invested_is_the_opening_plus_net_movements():
    movements = [(date(2023, 1, 15), d("4000.00")), (date(2023, 2, 1), d("-1000.00"))]

    assert total_invested(PREVIDENCIA, movements) == d("14036.00")
    assert total_invested([], []) == d("0.00")


# ---- A date range ---------------------------------------------------------------


def test_a_month_range_grows_like_the_spreadsheet_month():
    balance = balance_at_end_of(date(2023, 2, 28), PREVIDENCIA, [])
    invested = invested_during(date(2023, 2, 1), date(2023, 2, 28), PREVIDENCIA, [])

    assert balance == d("11451.00")  # February's closing
    assert invested == d("11196.00")  # January's closing
    assert balance - invested == d("255.00")


def test_income_in_the_range_is_invested_not_growth():
    points = [
        Point(date(2022, 12, 31), d("251567.20")),
        Point(date(2023, 1, 31), d("257523.00")),
    ]
    movements = [(date(2023, 1, 15), d("4000.00"))]

    balance = balance_at_end_of(date(2023, 1, 31), points, movements)
    invested = invested_during(date(2023, 1, 1), date(2023, 1, 31), points, movements)

    assert invested == d("255567.20")
    assert balance - invested == d("1955.80")


def test_a_range_without_a_closing_has_the_income_but_no_growth():
    points = PREVIDENCIA[:3]  # no March closing yet
    movements = [(date(2023, 3, 5), d("100.00"))]

    balance = balance_at_end_of(date(2023, 3, 31), points, movements)
    invested = invested_during(date(2023, 3, 1), date(2023, 3, 31), points, movements)

    assert balance == d("11551.00")
    assert balance - invested == d("0.00")


def test_a_range_with_the_opening_is_the_whole_life():
    balance = balance_at_end_of(date(2023, 3, 31), PREVIDENCIA, [])
    invested = invested_during(date(2022, 12, 1), date(2023, 3, 31), PREVIDENCIA, [])

    assert invested == total_invested(PREVIDENCIA, [])
    assert balance - invested == d("-29.00")  # 160 + 255 - 444


def test_a_range_before_the_opening_is_empty():
    balance = balance_at_end_of(date(2022, 11, 30), PREVIDENCIA, [])
    invested = invested_during(date(2022, 11, 1), date(2022, 11, 30), PREVIDENCIA, [])

    assert (balance, invested) == (d("0.00"), d("0.00"))


# ---- Growth % of a date range ----------------------------------------------------


def test_one_month_has_the_spreadsheet_percentage():
    points = [
        Point(date(2022, 12, 31), d("251567.20")),
        Point(date(2023, 1, 31), d("257523.00")),
    ]
    movements = [(date(2023, 1, 15), d("4000.00"))]

    months = growth_by_month(date(2023, 1, 1), date(2023, 1, 31), points, movements)

    assert months == {date(2023, 1, 1): MonthGrowth(d("251567.20"), d("1955.80"))}
    assert chained_percentage([months]) == 0.78  # the income isn't part of the base


def test_months_are_compounded():
    months = growth_by_month(date(2023, 1, 1), date(2023, 3, 31), PREVIDENCIA, [])

    # (1 + 160/11036) * (1 + 255/11196) * (1 - 444/11451) - 1
    assert chained_percentage([months]) == -0.26


def test_a_deposit_moves_neither_the_growth_nor_the_percentage():
    points = [
        Point(date(2022, 12, 31), d("1000.00")),  # opening
        Point(date(2023, 1, 31), d("2010.00")),  # +1%, then 1000 deposited
        Point(date(2023, 2, 28), d("2030.10")),  # +1% on everything
    ]
    movements = [(date(2023, 1, 31), d("1000.00"))]

    months = growth_by_month(date(2023, 1, 1), date(2023, 2, 28), points, movements)

    assert chained_percentage([months]) == 2.01  # 1.01 * 1.01 - 1


def test_investments_are_added_together_before_compounding():
    february = date(2023, 2, 1)
    small = {february: MonthGrowth(d("1000.00"), d("10.00"))}  # 1%
    large = {february: MonthGrowth(d("3000.00"), d("90.00"))}  # 3%

    assert chained_percentage([small, large]) == 2.5  # 100 / 4000


def test_a_month_without_a_saved_balance_adds_nothing():
    points = PREVIDENCIA[:3]  # no March closing yet

    months = growth_by_month(date(2023, 3, 1), date(2023, 3, 31), points, [])

    assert months == {}
    assert chained_percentage([months]) == 0.0
