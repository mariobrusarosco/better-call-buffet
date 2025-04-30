from typing import List
from sqlalchemy.orm import Session
from uuid import UUID

from app.domains.accounts.models import Account
from app.domains.accounts.schemas import AccountCreateRequest


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
        
    def create_account(self, account_in: AccountCreateRequest, user_id: UUID) -> Account:
        db_account = Account(
            **account_in.model_dump(), # Unpack fields from AccountCreateRequest
            user_id=user_id # Set the user ID from the dependency
        )
        self.db.add(db_account) # Add the new model instance to the session
        self.db.commit()
        self.db.refresh(db_account) # Refresh to get DB-generated values (like ID)
        return db_account # Return the newly created model instance
