from datetime import date, timedelta
from decimal import Decimal
from typing import Any

TWO_YEARS_IN_DAYS = 730


def validate_date_range_within_two_years(value: date) -> date:
    today = date.today()
    two_years_ago = today - timedelta(days=TWO_YEARS_IN_DAYS)

    if value < two_years_ago:
        raise ValueError(
            "Date is more than 2 years old",
            f"Only dates from {two_years_ago} onwards are allowed"
        )

    if value > today:
        raise ValueError(
            "Date {value} in the future",
            f"Only dates up to today ({today}) are allowed"
        )

    return value


def validate_balance_precision(value: Decimal) -> Decimal:
    value_str = str(value)
    
    if '.' in value_str:
        decimal_places = len(value_str.split(".")[1])

        if decimal_places > 2:
            raise ValueError(
                f"Balance has {decimal_places} decimal places, but maximum allowed is 2",
            )

    return value
