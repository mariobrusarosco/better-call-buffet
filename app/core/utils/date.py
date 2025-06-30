from datetime import datetime
from typing import Optional


def safe_parse_date(
    date_str: Optional[str], default: Optional[datetime] = None
) -> datetime:
    """
    🎓 Safely parse a date string with graceful fallback.

    This utility function encapsulates date parsing logic, making it reusable
    across different parts of the application where date parsing is needed.

    Args:
        date_str: Date string to parse (expected format: "YYYY-MM-DD") or None
        default: Default datetime to use if parsing fails

    Returns:
        Parsed datetime or default (current time if no default provided)

    Examples:
        >>> safe_parse_date("2024-01-15")
        datetime(2024, 1, 15, 0, 0)

        >>> safe_parse_date("invalid-date")
        datetime(2024, 1, 1, 12, 0, 0)  # Current time

        >>> safe_parse_date(None, datetime(2023, 12, 31))
        datetime(2023, 12, 31, 0, 0)
    """
    if not date_str:
        return default or datetime.utcnow()

    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return default or datetime.utcnow()


def safe_parse_datetime(
    datetime_str: Optional[str],
    format_str: str = "%Y-%m-%d %H:%M:%S",
    default: Optional[datetime] = None,
) -> datetime:
    """
    🎓 Safely parse a datetime string with custom format and graceful fallback.

    Args:
        datetime_str: Datetime string to parse or None
        format_str: Format string for parsing (default: "%Y-%m-%d %H:%M:%S")
        default: Default datetime to use if parsing fails

    Returns:
        Parsed datetime or default (current time if no default provided)
    """
    if not datetime_str:
        return default or datetime.utcnow()

    try:
        return datetime.strptime(datetime_str, format_str)
    except (ValueError, TypeError):
        return default or datetime.utcnow()
