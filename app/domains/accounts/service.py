from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from app.domains.accounts.models import Account


class AccountService:
    def __init__(self, db: Session):
        self.db = db

    def get_all_user_active_accounts(self, user_id: int) -> List[Account]:
        return self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.is_active == True
        ).all()


    def get_all_user_inactive_accounts(self, user_id: int) -> float:   
        return self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.is_active == False,
        ).all()
        