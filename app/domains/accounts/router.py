from fastapi import APIRouter, Depends
from typing import List
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.connection_and_session import get_db_session
from app.domains.accounts.schemas import Account, AccountCreateRequest
from app.domains.accounts.service import AccountService
from app.core.dependencies import get_current_user_id

router = APIRouter()

@router.get("/", response_model=List[Account])
def get_all_accounts_endpoint(
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id)
):
    account_service = AccountService(db)
    return account_service.get_all_user_active_accounts(user_id=current_user_id)


# Endpoint to get only ACTIVE accounts for a user
@router.get("/active", response_model=List[Account])
def get_active_accounts_endpoint(
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id)
):
    account_service = AccountService(db)
    return account_service.get_all_user_active_accounts(user_id=current_user_id)

@router.get("/inactive", response_model=List[Account])
def get_inactive_accounts_endpoint(
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id)
):
    account_service = AccountService(db)
    return account_service.get_all_user_inactive_accounts(user_id=current_user_id)


@router.post("/create", response_model=Account)
def create_account_endpoint(
    account_in: AccountCreateRequest,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id)
):
    account_service = AccountService(db)
    return account_service.create_account(account_in=account_in, user_id=current_user_id)

@router.get("/{account_id}", response_model=Account)
def get_account_endpoint(
    account_id: UUID,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id)
):
    account_service = AccountService(db)
    return account_service.get_account(account_id=account_id, user_id=current_user_id)
