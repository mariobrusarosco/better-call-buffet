from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.connection_and_session import get_db_session
from app.domains.accounts.schemas import Account, AccountIn, AccountType
from app.domains.accounts.service import AccountService
from app.core.dependencies import get_current_user_id

router = APIRouter()


@router.get("/", response_model=List[Account])
def get_all_accounts_endpoint(
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get all active accounts for the current user"""
    service = AccountService(db)
    return service.get_all_user_active_accounts(user_id=current_user_id)


@router.get("/active", response_model=List[Account])
def get_active_accounts_endpoint(
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get only active accounts for the current user"""
    service = AccountService(db)
    return service.get_all_user_active_accounts(user_id=current_user_id)


@router.get("/inactive", response_model=List[Account])
def get_inactive_accounts_endpoint(
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get only inactive accounts for the current user"""
    service = AccountService(db)
    return service.get_all_user_inactive_accounts(user_id=current_user_id)


@router.get("/balance/total")
def get_total_balance_endpoint(
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get total balance across all active accounts"""
    service = AccountService(db)
    total_balance = service.get_user_total_balance(current_user_id)
    return {"total_balance": total_balance}


@router.get("/balance/by-currency/{currency}")
def get_balance_by_currency_endpoint(
    currency: str,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get total balance for a specific currency"""
    service = AccountService(db)
    balance = service.get_user_balance_by_currency(current_user_id, currency.upper())
    return {"currency": currency.upper(), "balance": balance}


@router.get("/type/{account_type}", response_model=List[Account])
def get_accounts_by_type_endpoint(
    account_type: AccountType,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get all active accounts of a specific type"""
    service = AccountService(db)
    return service.get_accounts_by_type(current_user_id, account_type)


@router.post("/", response_model=Account)
def create_account_endpoint(
    account_in: AccountIn,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Create a new account"""
    service = AccountService(db)
    try:
        return service.create_account(account_in=account_in, user_id=current_user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{account_id}", response_model=Account)
def get_account_endpoint(
    account_id: UUID,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get a specific account by ID"""
    service = AccountService(db)
    account = service.get_account_by_id(account_id=account_id, user_id=current_user_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.patch("/{account_id}/balance")
def update_account_balance_endpoint(
    account_id: UUID,
    new_balance: float,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Update account balance"""
    service = AccountService(db)
    try:
        account = service.update_account_balance(
            account_id, current_user_id, new_balance
        )
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        return {
            "message": "Balance updated successfully",
            "new_balance": account.balance,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{account_id}")
def deactivate_account_endpoint(
    account_id: UUID,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Deactivate an account (soft delete)"""
    service = AccountService(db)
    account = service.deactivate_account(account_id, current_user_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"message": "Account deactivated successfully"}
