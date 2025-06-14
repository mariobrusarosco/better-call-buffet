from typing import List
from sqlalchemy.orm import Session, joinedload
from uuid import UUID

from app.domains.accounts.models import Account
from app.domains.accounts.schemas import AccountIn, AccountType, AccountWithBroker
from app.domains.brokers.models import Broker


class AccountService:
    def __init__(self, db: Session):
        self.db = db

    def get_all_user_active_accounts(self, user_id: UUID) -> List[Account]:
        return self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.is_active == True
        ).all()


    def get_all_user_inactive_accounts(self, user_id: UUID) -> List[Account]:   
        return self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.is_active == False,
        ).all()
        
    def create_account(self, account_in: AccountIn, user_id: UUID) -> Account:
        db_account = Account(
            **account_in.model_dump(), # Unpack fields from AccountIn
            user_id=user_id # Set the user ID from the dependency
        )
        self.db.add(db_account) # Add the new model instance to the session
        self.db.commit()
        self.db.refresh(db_account) # Refresh to get DB-generated values (like ID)
        return db_account # Return the newly created model instance

    def get_account_by_id(self, account_id: UUID, user_id: UUID) -> AccountWithBroker:
        return self.db.query(Account).options(
            joinedload(Account.broker)  # This will eagerly load the broker relationship
        ).join( 
            Broker,
            Account.broker_id == Broker.id
        ).filter(
            Account.id == account_id,
            Account.user_id == user_id
        ).first()

    def get_accounts_by_type(self, user_id: UUID, account_type: AccountType) -> List[Account]:
        """Get all active accounts of a specific type for a user"""
        return self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.type == account_type,
            Account.is_active == True
        ).all()

