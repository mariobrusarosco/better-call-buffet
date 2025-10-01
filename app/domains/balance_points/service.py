from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.domains.balance_points.models import BalancePoint
from app.domains.balance_points.repository import BalancePointRepository
from app.domains.balance_points.schemas import BalancePointIn
from app.domains.transactions.repository import TransactionRepository
from app.domains.accounts.repository import AccountRepository


class BalancePointService:
    """
    Service layer for BalancePoint business logic.
    Uses BalancePointRepository for data access operations.
    """

    def __init__(self, db: Session):
        self.repository = BalancePointRepository(db)
        self.account_repository = AccountRepository(db)
        self.transaction_repository = TransactionRepository(db)

    ## ------- REVISION THRESHOLD -------
    
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
        account = self.account_repository.get_by_id_and_user(
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
            "snapshot_type": balance_point_in.snapshot_type,
            "note": balance_point_in.note,
        }

        return self.repository.create(balance_point_data)

    def get_balance_points_by_account_id(
        self, account_id: UUID, user_id: UUID
    ) -> List[BalancePoint]:
        """Get all balance points for a specific account"""
        # Validate account ownership
        account = self.account_repository.get_by_id_and_user(account_id, user_id)
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
        account = self.account_repository.get_by_id_and_user(account_id, user_id)
        if not account:
            raise ValueError("Account not found or does not belong to user")

        return self.repository.get_account_balance_trend(account_id, user_id, days)

    def get_latest_balance_by_account(
        self, account_id: UUID, user_id: UUID
    ) -> Optional[BalancePoint]:
        """Get the most recent balance point for an account"""
        # Validate account ownership
        account = self.account_repository.get_by_id_and_user(account_id, user_id)
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

    def get_monthly_summaries(
        self, account_id: UUID, user_id: UUID, year: int = None, months: int = 12
    ) -> List[dict]:
        """
        Get monthly balance summaries for an account.
        Shows starting balance, ending balance, movement, and profit percentage for each month.
        
        Args:
            account_id: ID of the account
            user_id: ID of the user
            year: Year to get summaries for (defaults to current year)
            months: Number of months to return (defaults to 12, max 12)
        
        Returns:
            List of monthly summaries with balance data
        """
        # Validate account ownership
        account = self.account_repository.get_by_id_and_user(account_id, user_id)
        if not account:
            raise ValueError("Account not found or does not belong to user")
        
        return self.repository.get_monthly_summaries(account_id, user_id, year, months)

    def upsert_balance_point(
        self, 
        account_id: UUID, 
        target_date: datetime,
        balance_data: dict,
        user_id: UUID
    ) -> BalancePoint:
        """
        Create or update a balance point for a specific account and date.
        
        Args:
            account_id: ID of the account
            target_date: Date for the balance point
            balance_data: Balance point data (balance, snapshot_type, note)
            user_id: ID of the user
        
        Returns:
            The created or updated balance point
        
        Raises:
            ValueError: If account doesn't belong to user
        """
        # Validate account ownership
        account = self.account_repository.get_by_id_and_user(account_id, user_id)
        if not account:
            raise ValueError("Account not found or does not belong to user")
        
        # Convert datetime to date if needed
        if isinstance(target_date, datetime):
            target_date = target_date.date()
        
        # Call repository upsert method
        return self.repository.upsert(account_id, user_id, target_date, balance_data)

    def calculate_account_balance_from_transactions(
        self, account_id: UUID, user_id: UUID
    ) -> float:
        """
        Calculate account balance using smart incremental logic with balance points.
        
        Performance Strategy:
        1. Find latest balance point for account (if any)
        2. If balance point exists: latest_balance + sum(transactions_since_calculated_at)
        3. If no balance point: fallback to full calculation from opening balance
        
        This approach transforms O(all_transactions) to O(recent_transactions).
        
        Args:
            account_id: ID of the account
            user_id: ID of the user (for security validation)
            
        Returns:
            Current calculated balance
            
        Raises:
            ValueError: If account doesn't belong to user
        """
        # Validate account ownership
        account = self.account_repository.get_by_id_and_user(account_id, user_id)
        if not account:
            raise ValueError("Account not found or does not belong to user")
        
        # SMART APPROACH: Try to use latest balance point + delta
        latest_balance_point = self.repository.get_latest_by_account(account_id, user_id)
        
        if latest_balance_point:
            base_balance = float(latest_balance_point.balance)
            delta_transactions = self.transaction_repository.get_account_transactions_since_timestamp(
                account_id=account_id,
                user_id=user_id,
                since_timestamp=latest_balance_point.calculated_at
            )
            
            delta_impact = sum(
                float(transaction.balance_impact or 0) for transaction in delta_transactions
            )
            
            return base_balance + delta_impact
        
        else:
            # This only happens when user hasn't created any balance points yet
            # Get opening balance from opening balance point
            balance_points = self.repository.get_by_account_and_user(account_id, user_id)
            opening_balance_point = next(
                (bp for bp in balance_points if bp.snapshot_type == "opening"), None
            )
            initial_balance = float(opening_balance_point.balance) if opening_balance_point else 0.0
            
            transactions, _ = self.transaction_repository.get_account_transactions_with_filters(
                account_id=account_id, 
                user_id=user_id,
                filters=None  # No filters to get all transactions
            )
            
            # Sum all balance impacts
            transaction_impacts = sum(
                float(transaction.balance_impact or 0) for transaction in transactions
            )
            
            return initial_balance + transaction_impacts

    def create_balance_snapshot_from_transactions(
        self, account_id: UUID, user_id: UUID, note: str = None
    ) -> BalancePoint:
        """
        Create today's balance snapshot by calculating balance from transactions.
        """
        # Calculate current balance from transactions
        calculated_balance = self.calculate_account_balance_from_transactions(
            account_id, user_id
        )
        
        # Create/update today's balance point with calculated balance
        today = datetime.utcnow()
        balance_data = {
            "balance": calculated_balance,
            "snapshot_type": "manual",
            "note": note
        }
        
        return self.upsert_balance_point(
            account_id=account_id,
            target_date=today,
            balance_data=balance_data,
            user_id=user_id
        )

    def auto_update_balance_from_transaction(
        self, account_id: UUID, transaction_id: UUID, user_id: UUID
    ) -> BalancePoint:
        # Get the transaction to use its date for the balance point
        transaction = self.transaction_repository.get_by_id(transaction_id)
        if not transaction:
            raise ValueError(f"Transaction {transaction_id} not found")
        
        # Calculate new balance using smart incremental logic
        calculated_balance = self.calculate_account_balance_from_transactions(
            account_id, user_id
        )
        
        # Create/update balance point for the transaction's date (not today!)
        transaction_date = transaction.date
        balance_data = {
            "balance": calculated_balance,
            "snapshot_type": "transaction",  # Automatic update from transaction
            "note": f"Auto-updated from transaction",
            "source_transaction_id": transaction_id
        }
        
        return self.upsert_balance_point(
            account_id=account_id,
            target_date=transaction_date,
            balance_data=balance_data,
            user_id=user_id
        )

    def auto_update_balance_from_transaction_deletion(
        self, account_id: UUID, deleted_transaction_date: datetime, user_id: UUID
    ) -> BalancePoint:
        """
        Auto-update account balance after a transaction deletion.
        
        Args:
            account_id: ID of the account that had the transaction
            deleted_transaction_date: Date of the deleted transaction
            user_id: ID of the user
            
        Returns:
            Updated balance point
            
        Raises:
            ValueError: If account doesn't belong to user
        """
        # Validate account ownership
        account = self.account_repository.get_by_id_and_user(account_id, user_id)
        if not account:
            raise ValueError("Account not found or does not belong to user")
        
        # Calculate new balance using smart incremental logic
        calculated_balance = self.calculate_account_balance_from_transactions(
            account_id, user_id
        )
        
        # Create/update balance point for the transaction's date
        balance_data = {
            "balance": calculated_balance,
            "snapshot_type": "transaction",
            "note": "Auto-updated after transaction deletion",
            "source_transaction_id": None  # No source transaction since it was deleted
        }
        
        return self.upsert_balance_point(
            account_id=account_id,
            target_date=deleted_transaction_date,
            balance_data=balance_data,
            user_id=user_id
        )

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
