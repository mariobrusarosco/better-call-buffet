from datetime import date, timedelta
from typing import Union


class BalancePointValidationError(Exception):
    """Custom exception for balance point validation errors."""
    pass


def validate_transaction_date(transaction_date: Union[date, str]) -> bool:
    """
    Validate that a transaction date is within the allowed 2-year window.
    
    Args:
        transaction_date: The transaction date to validate (date object or ISO string)
        
    Returns:
        bool: True if valid
        
    Raises:
        BalancePointValidationError: If transaction date is older than 2 years
        ValueError: If date format is invalid
    """
    # Convert string to date if needed
    if isinstance(transaction_date, str):
        try:
            transaction_date = date.fromisoformat(transaction_date)
        except ValueError:
            raise ValueError(f"Invalid date format: {transaction_date}. Expected YYYY-MM-DD format.")
    
    # Calculate 2 years ago from today
    two_years_ago = date.today() - timedelta(days=730)
    
    # Validate the transaction date
    if transaction_date < two_years_ago:
        raise BalancePointValidationError(
            f"Transaction date {transaction_date} is older than 2 years. "
            f"Transactions older than {two_years_ago} are not allowed."
        )
    
    return True


def validate_balance_precision(balance: Union[int, float, str]) -> bool:
    """
    Validate that a balance value fits within DECIMAL(15,2) precision.
    
    Args:
        balance: The balance value to validate
        
    Returns:
        bool: True if valid
        
    Raises:
        BalancePointValidationError: If balance exceeds precision limits
    """
    from decimal import Decimal, InvalidOperation
    
    try:
        decimal_balance = Decimal(str(balance))
    except (InvalidOperation, ValueError):
        raise BalancePointValidationError(f"Invalid balance value: {balance}")
    
    # Check precision limits for DECIMAL(15,2)
    max_value = Decimal('999999999999999.99')
    min_value = Decimal('-999999999999999.99')
    
    if decimal_balance > max_value or decimal_balance < min_value:
        raise BalancePointValidationError(
            f"Balance {balance} exceeds precision limits. "
            f"Must be between {min_value} and {max_value}."
        )
    
    return True


def validate_timeline_status(status: str) -> bool:
    """
    Validate that timeline status is one of the allowed values.
    
    Args:
        status: The status to validate
        
    Returns:
        bool: True if valid
        
    Raises:
        BalancePointValidationError: If status is not allowed
    """
    allowed_statuses = {'current', 'updating', 'failed'}
    
    if status not in allowed_statuses:
        raise BalancePointValidationError(
            f"Invalid timeline status: {status}. "
            f"Must be one of: {', '.join(sorted(allowed_statuses))}"
        )
    
    return True


def validate_account_date_uniqueness(db_session, account_id: str, date_value: date, exclude_id: str = None) -> bool:
    """
    Validate that no balance point exists for the given account and date.
    
    Args:
        db_session: Database session
        account_id: The account ID to check
        date_value: The date to check
        exclude_id: Optional balance point ID to exclude from check (for updates)
        
    Returns:
        bool: True if unique
        
    Raises:
        BalancePointValidationError: If balance point already exists for account and date
    """
    from app.domains.balance_points.models import BalancePoint
    from sqlalchemy import and_
    
    query = db_session.query(BalancePoint).filter(
        and_(
            BalancePoint.account_id == account_id,
            BalancePoint.date == date_value
        )
    )
    
    # Exclude specific ID if provided (for update operations)
    if exclude_id:
        query = query.filter(BalancePoint.id != exclude_id)
    
    existing = query.first()
    
    if existing:
        raise BalancePointValidationError(
            f"Balance point already exists for account {account_id} on date {date_value}. "
            f"Each account can only have one balance point per day."
        )
    
    return True