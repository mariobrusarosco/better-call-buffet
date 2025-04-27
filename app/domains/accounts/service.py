from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from app.domains.accounts.models import Account


class AccountService:
    def __init__(self, db: Session):
        self.db = db

        # For now, just sum up balances for the given currency
        # In a real app, you would add currency conversion
        accounts = self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.is_active == True,
            Account.currency == currency
        ).all()
        
        return sum(account.balance for account in accounts) 