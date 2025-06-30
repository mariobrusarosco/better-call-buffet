from decimal import Decimal, InvalidOperation
from typing import Optional, Union


def safe_parse_float(value: Optional[str], default: float = 0.0) -> float:
    """
    🎓 Safely parse a numeric string to float with graceful fallback.

    This utility function handles amount parsing with sensible defaults,
    ensuring the system continues processing even with malformed data.

    Args:
        value: String value to convert to float or None
        default: Default float value if parsing fails

    Returns:
        Parsed float or default value

    Examples:
        >>> safe_parse_float("123.45")
        123.45

        >>> safe_parse_float("invalid")
        0.0

        >>> safe_parse_float(None, 100.0)
        100.0
    """
    if not value:
        return default

    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_parse_int(value: Optional[str], default: int = 0) -> int:
    """
    🎓 Safely parse a numeric string to integer with graceful fallback.

    Args:
        value: String value to convert to int or None
        default: Default int value if parsing fails

    Returns:
        Parsed int or default value
    """
    if not value:
        return default

    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_parse_decimal(
    value: Optional[str], default: Union[Decimal, float] = Decimal("0.0")
) -> Decimal:
    """
    🎓 Safely parse a numeric string to Decimal with graceful fallback.

    Decimal is preferred for financial calculations due to precision.

    Args:
        value: String value to convert to Decimal or None
        default: Default Decimal value if parsing fails

    Returns:
        Parsed Decimal or default value
    """
    if not value:
        return Decimal(str(default))

    try:
        return Decimal(value)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(str(default))


def format_currency(amount: Union[float, Decimal], currency_symbol: str = "$") -> str:
    """
    🎓 Format a numeric amount as currency string.

    Args:
        amount: Numeric amount to format
        currency_symbol: Currency symbol to use

    Returns:
        Formatted currency string

    Examples:
        >>> format_currency(123.45)
        "$123.45"

        >>> format_currency(1234.56, "€")
        "€1,234.56"
    """
    try:
        return f"{currency_symbol}{amount:,.2f}"
    except (ValueError, TypeError):
        return f"{currency_symbol}0.00"
