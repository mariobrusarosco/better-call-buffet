from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from app.domains.accounts.models import Account
from app.domains.accounts.schemas import AccountCreate, AccountUpdate, AccountSummary
from app.domains.users.models import User

class AccountService:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, account_id: int) -> Optional[Account]:
        return self.db.query(Account).filter(Account.id == account_id).first()
        
    def get_by_user_id(self, user_id: int, skip: int = 0, limit: int = 100) -> List[Account]:
        return self.db.query(Account).filter(Account.user_id == user_id).offset(skip).limit(limit).all()
    
    def get_active_by_user_id(self, user_id: int) -> List[Account]:
        return self.db.query(Account).filter(Account.user_id == user_id, Account.is_active == True).all()
        
    def create(self, user_id: int, account_in: AccountCreate) -> Account:
        # First check if user exists
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User with ID {user_id} not found")
            
        # Create the account
        db_account = Account(
            name=account_in.name,
            description=account_in.description,
            type=account_in.type.value,
            balance=account_in.balance,
            currency=account_in.currency,
            is_active=account_in.is_active,
            user_id=user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        self.db.add(db_account)
        self.db.commit()
        self.db.refresh(db_account)
        return db_account
        
    def update(self, account_id: int, account_in: AccountUpdate) -> Optional[Account]:
        db_account = self.get_by_id(account_id=account_id)
        if not db_account:
            return None
            
        update_data = account_in.dict(exclude_unset=True)
        
        # Convert enum to string value if present
        if "type" in update_data and update_data["type"]:
            update_data["type"] = update_data["type"].value
            
        for field, value in update_data.items():
            setattr(db_account, field, value)
            
        db_account.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(db_account)
        return db_account
        
    def delete(self, account_id: int) -> bool:
        db_account = self.get_by_id(account_id=account_id)
        if not db_account:
            return False
            
        self.db.delete(db_account)
        self.db.commit()
        return True
        
    def deactivate(self, account_id: int) -> Optional[Account]:
        db_account = self.get_by_id(account_id=account_id)
        if not db_account:
            return None
            
        db_account.is_active = False
        db_account.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(db_account)
        return db_account
        
    def get_total_balance(self, user_id: int, currency: str = "USD") -> float:
        # For now, just sum up balances for the given currency
        # In a real app, you would add currency conversion
        accounts = self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.is_active == True,
            Account.currency == currency
        ).all()
        
        return sum(account.balance for account in accounts) 