from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from uuid import UUID

from app.domains.accounts.models import Account
from app.domains.accounts.schemas import AccountIn, AccountType
from app.domains.brokers.models import Broker


class AccountRepository:
    """
    Repository pattern implementation for Account entity.
    Abstracts all database operations and provides a clean interface for data access.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_user_and_status(self, user_id: UUID, is_active: bool) -> List[Account]:
        """Get accounts by user ID and active status"""
        return (
            self.db.query(Account)
            .filter(Account.user_id == user_id, Account.is_active == is_active)
            .all()
        )

    def get_active_accounts_by_user(self, user_id: UUID) -> List[Account]:
        """Get all active accounts for a user"""
        return self.get_by_user_and_status(user_id, is_active=True)

    def get_inactive_accounts_by_user(self, user_id: UUID) -> List[Account]:
        """Get all inactive accounts for a user"""
        return self.get_by_user_and_status(user_id, is_active=False)

    def get_by_id_and_user(self, account_id: UUID, user_id: UUID) -> Optional[Account]:
        """Get account by ID and user ID with broker relationship loaded"""
        return (
            self.db.query(Account)
            .options(joinedload(Account.broker))  # Eagerly load the broker relationship
            .join(Broker, Account.broker_id == Broker.id)
            .filter(Account.id == account_id, Account.user_id == user_id)
            .first()
        )

    def get_by_type_and_user(
        self, user_id: UUID, account_type: AccountType, is_active: bool = True
    ) -> List[Account]:
        """Get accounts by type and user ID, optionally filtered by active status"""
        return (
            self.db.query(Account)
            .filter(
                Account.user_id == user_id,
                Account.type == account_type,
                Account.is_active == is_active,
            )
            .all()
        )

    def create(self, account_data: dict) -> Account:
        """Create a new account"""
        db_account = Account(**account_data)
        self.db.add(db_account)
        self.db.commit()
        self.db.refresh(db_account)
        return db_account

    def update(self, account: Account, update_data: dict) -> Account:
        """Update an existing account"""
        for key, value in update_data.items():
            if hasattr(account, key):
                setattr(account, key, value)

        self.db.commit()
        self.db.refresh(account)
        return account

    def delete(self, account: Account) -> None:
        """Delete an account (hard delete)"""
        self.db.delete(account)
        self.db.commit()

    def soft_delete(self, account: Account) -> Account:
        """Soft delete an account by setting is_active to False"""
        account.is_active = False
        self.db.commit()
        self.db.refresh(account)
        return account

    def exists_by_name_and_user(
        self, name: str, user_id: UUID, exclude_id: Optional[UUID] = None
    ) -> bool:
        """Check if an account with the given name exists for a user"""
        query = self.db.query(Account).filter(
            Account.name == name, Account.user_id == user_id
        )

        if exclude_id:
            query = query.filter(Account.id != exclude_id)

        return query.first() is not None

    def get_total_balance_by_user(self, user_id: UUID) -> float:
        """Calculate total balance across all active accounts for a user"""
        result = (
            self.db.query(Account)
            .filter(Account.user_id == user_id, Account.is_active == True)
            .all()
        )

        return sum(account.balance for account in result)

    def get_balance_by_currency(self, user_id: UUID, currency: str) -> float:
        """Get total balance for a specific currency"""
        result = (
            self.db.query(Account)
            .filter(
                Account.user_id == user_id,
                Account.currency == currency,
                Account.is_active == True,
            )
            .all()
        )

        return sum(account.balance for account in result)
