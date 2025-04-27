from fastapi import APIRouter, Depends
from typing import List
from sqlalchemy.orm import Session

from app.db.base import get_db_session
from app.domains.accounts.schemas import Account
from app.domains.accounts.service import AccountService
from app.core.dependencies import get_current_user_id

router = APIRouter()

@router.get("/", response_model=List[Account])
def read_all_accounts(
    db: Session = Depends(get_db_session),
    current_user_id: int = Depends(get_current_user_id)
):
    account_service = AccountService(db)
    return account_service.get_all_user_active_accounts(user_id=current_user_id)


# Endpoint to get only ACTIVE accounts for a user
@router.get("/active", response_model=List[Account])
def read_active_accounts(
    db: Session = Depends(get_db_session),
    current_user_id: int = Depends(get_current_user_id)
):
    account_service = AccountService(db)
    return account_service.get_all_user_active_accounts(user_id=current_user_id)

@router.get("/inactive", response_model=List[Account])
def read_inactive_accounts(
    db: Session = Depends(get_db_session),
    current_user_id: int = Depends(get_current_user_id)
):
    account_service = AccountService(db)
    return account_service.get_all_user_inactive_accounts(user_id=current_user_id)