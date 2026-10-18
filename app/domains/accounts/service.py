from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.domains.accounts.models import Account
from app.domains.accounts.repository import AccountRepository
from app.domains.accounts.schemas import (
    AccountCreateIn,
    AccountType,
    AccountWithBalance,
)
from app.domains.balance_points.service import BalancePointService


class AccountService:

    def __init__(self, db: Session):
        self.db = db
        self.repository = AccountRepository(db)
        self.balance_point_service = BalancePointService(db)

    def get_account_by_id(
        self, account_id: UUID, user_id: UUID
    ) -> Optional[AccountWithBalance]:
        account = self.repository.get_by_id_and_user(account_id, user_id)
        if account:
            balance = self.balance_point_service.calculate_account_balance(
                account_id, user_id
            )
            # Set the calculated balance
            account.balance = balance
        return account

    def create_account(self, account_in: AccountCreateIn, user_id: UUID) -> Account:
        # Business logic: Check if account name already exists for this user
        if self.repository.exists_by_name_and_user(account_in.name, user_id):
            raise ValueError(f"Account with name '{account_in.name}' already exists")

        initial_balance = account_in.balance

        # The balance and opening date belong to the opening point, not the account
        account_data = account_in.model_dump(exclude={"balance", "opening_date"})
        account_data["user_id"] = user_id
        # Account and opening point are one atomic operation. Either both are
        # committed or neither is persisted.
        try:
            created_account = self.repository.create(account_data, commit=False)
            self.balance_point_service.create_opening_balance_point(
                account_id=created_account.id,
                opening_date=account_in.opening_date
                or created_account.created_at.date(),
                opening_balance=Decimal(str(initial_balance)),
                commit=False,
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        persisted_account = self.repository.get_by_id_and_user(
            created_account.id, user_id
        )
        if persisted_account is None:
            raise RuntimeError("Created account could not be reloaded")
        return persisted_account

    ## ------- REVISION THRESHOLD -------
    def get_user_accounts(
        self,
        user_id: UUID,
        is_active: bool = True,
        account_type: Optional[AccountType] = None,
    ) -> List[AccountWithBalance]:
        """Get a user's accounts filtered by status and type, with calculated balances"""
        accounts = self.repository.get_by_user_and_status(
            user_id, is_active=is_active, account_type=account_type
        )

        # Calculate balance for each account
        for account in accounts:
            account.balance = self.balance_point_service.calculate_account_balance(
                account.id, user_id
            )

        return accounts

    def get_all_user_active_accounts(self, user_id: UUID) -> List[AccountWithBalance]:
        """Get all active accounts for a user with calculated balances"""
        accounts = self.repository.get_active_accounts_by_user(user_id)

        # Calculate balance for each account
        for account in accounts:
            balance = self.balance_point_service.calculate_account_balance(
                account.id, user_id
            )
            account.balance = balance

        return accounts

    def get_all_user_inactive_accounts(self, user_id: UUID) -> List[AccountWithBalance]:
        """Get all inactive accounts for a user with calculated balances"""
        accounts = self.repository.get_inactive_accounts_by_user(user_id)

        # Calculate balance for each account
        for account in accounts:
            calculated_balance = self.balance_point_service.calculate_account_balance(
                account.id, user_id
            )
            account.balance = calculated_balance

        return accounts

    def get_accounts_by_type(
        self, user_id: UUID, account_type: AccountType
    ) -> List[Account]:
        """Get all active accounts of a specific type for a user"""
        return self.repository.get_by_type_and_user(
            user_id, account_type, is_active=True
        )

    def update_account_balance(
        self, account_id: UUID, user_id: UUID, new_balance: float
    ) -> Optional[Account]:
        """
        Update account balance with business logic validation.

        Args:
            account_id: ID of the account to update
            user_id: ID of the user updating the account
            new_balance: New balance value

        Returns:
            Updated account if successful, None if account not found

        Raises:
            ValueError: If new balance is negative
        """
        if new_balance < 0:
            raise ValueError("Account balance cannot be negative")

        account = self.repository.get_by_id_and_user(account_id, user_id)
        if not account:
            return None

        return self.repository.update(account, {"balance": new_balance})

    def deactivate_account(self, account_id: UUID, user_id: UUID) -> Optional[Account]:
        """
        Deactivate an account (soft delete).

        Args:
            account_id: ID of the account to deactivate
            user_id: ID of the user deactivating the account

        Returns:
            Deactivated account if successful, None if account not found
        """
        account = self.repository.get_by_id_and_user(account_id, user_id)
        if not account:
            return None

        return self.repository.soft_delete(account)

    def get_user_total_balance(self, user_id: UUID) -> Decimal:
        """
        Calculate total balance across all active accounts for a user.

        Args:
            user_id: ID of the user

        Returns:
            Total balance across all active accounts
        """
        accounts = self.repository.get_active_accounts_by_user(user_id)
        return sum(
            (
                self.balance_point_service.calculate_account_balance(
                    account.id, user_id
                )
                for account in accounts
            ),
            Decimal("0.00"),
        )

    def get_user_balance_by_currency(self, user_id: UUID, currency: str) -> Decimal:
        """
        Get total balance for a specific currency.

        Args:
            user_id: ID of the user
            currency: Currency code (e.g., 'BRL', 'USD')

        Returns:
            Total balance for the specified currency
        """
        accounts = self.repository.get_active_accounts_by_user(user_id)
        return sum(
            (
                self.balance_point_service.calculate_account_balance(
                    account.id, user_id
                )
                for account in accounts
                if account.currency == currency
            ),
            Decimal("0.00"),
        )
