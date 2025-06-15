from typing import List, Optional
from datetime import datetime, date
from uuid import UUID
from sqlalchemy.orm import Session

from app.domains.balance_points.models import BalancePoint
from app.domains.balance_points.schemas import BalancePointIn
from app.domains.balance_points.repository import BalancePointRepository
from app.domains.accounts.service import AccountService


class BalancePointService:
    """
    Service layer for BalancePoint business logic.
    Uses BalancePointRepository for data access operations.
    """

    def __init__(self, db: Session):
        self.repository = BalancePointRepository(db)
        self.account_service = AccountService(db)

    def create_balance_point(
        self, balance_point_in: BalancePointIn, user_id: UUID
    ) -> BalancePoint:
        """
        Create a new balance point with business logic validation.

        Args:
            balance_point_in: Balance point creation data
            user_id: ID of the user creating the balance point

        Returns:
            The created balance point

        Raises:
            ValueError: If account doesn't belong to user or duplicate date entry
        """
        # Validate account ownership
        account = self.account_service.get_account_by_id(
            balance_point_in.account_id, user_id
        )
        if not account:
            raise ValueError("Account not found or does not belong to user")

        # Check for duplicate balance point on the same date
        target_date = (
            balance_point_in.date.date()
            if balance_point_in.date
            else datetime.utcnow().date()
        )
        if self.repository.exists_for_account_and_date(
            balance_point_in.account_id, user_id, target_date
        ):
            raise ValueError(
                f"Balance point already exists for this account on {target_date}"
            )

        # Prepare balance point data
        balance_point_data = {
            "user_id": user_id,
            "account_id": balance_point_in.account_id,
            "date": balance_point_in.date or datetime.utcnow(),
            "balance": balance_point_in.balance,
            "note": balance_point_in.note,
        }

        return self.repository.create(balance_point_data)

    def get_balance_points_by_account_id(
        self, account_id: UUID, user_id: UUID
    ) -> List[BalancePoint]:
        """Get all balance points for a specific account"""
        # Validate account ownership
        account = self.account_service.get_account_by_id(account_id, user_id)
        if not account:
            raise ValueError("Account not found or does not belong to user")

        return self.repository.get_by_account_and_user(account_id, user_id)

    def get_balance_point_by_id(
        self, balance_point_id: UUID, user_id: UUID
    ) -> Optional[BalancePoint]:
        """Get a specific balance point by ID"""
        return self.repository.get_by_id_and_user(balance_point_id, user_id)

    def update_balance_point(
        self, balance_point_id: UUID, user_id: UUID, update_data: dict
    ) -> Optional[BalancePoint]:
        """
        Update a balance point with business logic validation.

        Args:
            balance_point_id: ID of the balance point to update
            user_id: ID of the user updating the balance point
            update_data: Dictionary of fields to update

        Returns:
            Updated balance point if successful, None if not found

        Raises:
            ValueError: If validation fails
        """
        balance_point = self.repository.get_by_id_and_user(balance_point_id, user_id)
        if not balance_point:
            return None

        # If updating date, check for conflicts
        if "date" in update_data:
            new_date = (
                update_data["date"].date()
                if isinstance(update_data["date"], datetime)
                else update_data["date"]
            )
            if self.repository.exists_for_account_and_date(
                balance_point.account_id, user_id, new_date
            ):
                current_date = balance_point.date.date()
                if (
                    new_date != current_date
                ):  # Only raise error if it's a different date
                    raise ValueError(
                        f"Balance point already exists for this account on {new_date}"
                    )

        # Validate balance is not negative
        if "balance" in update_data and update_data["balance"] < 0:
            raise ValueError("Balance cannot be negative")

        return self.repository.update(balance_point, update_data)

    def delete_balance_point(self, balance_point_id: UUID, user_id: UUID) -> bool:
        """Delete a balance point"""
        balance_point = self.repository.get_by_id_and_user(balance_point_id, user_id)
        if not balance_point:
            return False

        self.repository.delete(balance_point)
        return True

    def get_balance_history_with_movements(
        self, user_id: UUID, account_id: Optional[UUID] = None
    ) -> List[dict]:
        """
        Get balance history with calculated movements between consecutive points.
        This provides the "DIFF" functionality similar to Excel sheets.

        Args:
            user_id: ID of the user
            account_id: Optional account ID to filter by specific account

        Returns:
            List of balance points with movement calculations
        """
        return self.repository.get_balance_history_summary(user_id, account_id)

    def get_balance_trend(
        self, account_id: UUID, user_id: UUID, days: int = 30
    ) -> List[BalancePoint]:
        """
        Get balance trend for an account over specified days.
        Useful for charting and analytics.

        Args:
            account_id: ID of the account
            user_id: ID of the user
            days: Number of days to look back (default 30)

        Returns:
            List of balance points ordered by date
        """
        # Validate account ownership
        account = self.account_service.get_account_by_id(account_id, user_id)
        if not account:
            raise ValueError("Account not found or does not belong to user")

        return self.repository.get_account_balance_trend(account_id, user_id, days)

    def get_latest_balance_by_account(
        self, account_id: UUID, user_id: UUID
    ) -> Optional[BalancePoint]:
        """Get the most recent balance point for an account"""
        # Validate account ownership
        account = self.account_service.get_account_by_id(account_id, user_id)
        if not account:
            raise ValueError("Account not found or does not belong to user")

        return self.repository.get_latest_by_account(account_id, user_id)

    def get_balance_points_by_date_range(
        self, user_id: UUID, start_date: datetime, end_date: datetime
    ) -> List[BalancePoint]:
        """Get balance points within a date range across all accounts"""
        if start_date > end_date:
            raise ValueError("Start date must be before end date")

        return self.repository.get_by_user_and_date_range(user_id, start_date, end_date)

    def get_total_balance_at_date(self, user_id: UUID, target_date: date) -> float:
        """
        Calculate total balance across all accounts at a specific date.
        Uses the latest balance point for each account up to that date.

        Args:
            user_id: ID of the user
            target_date: Date to calculate balance for

        Returns:
            Total balance across all accounts at the specified date
        """
        return self.repository.get_total_balance_at_date(user_id, target_date)
