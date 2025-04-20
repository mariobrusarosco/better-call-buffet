from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.domains.accounts.schemas import Account, AccountCreate, AccountUpdate, AccountSummary
from app.domains.accounts.service import AccountService

router = APIRouter()

@router.post("/", response_model=Account)
def create_account(
    account_in: AccountCreate,
    user_id: int,  # This will be replaced with actual auth mechanism
    db: Session = Depends(get_db)
):
    """
    Create a new account for the current user.
    """
    account_service = AccountService(db)
    return account_service.create(user_id=user_id, account_in=account_in)

@router.get("/", response_model=List[Account])
def read_accounts(
    user_id: int,  # This will be replaced with actual auth mechanism
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Retrieve accounts for the current user.
    """
    account_service = AccountService(db)
    return account_service.get_by_user_id(user_id=user_id, skip=skip, limit=limit)

@router.get("/active", response_model=List[AccountSummary])
def read_active_accounts(
    user_id: int,  # This will be replaced with actual auth mechanism
    db: Session = Depends(get_db)
):
    """
    Retrieve active accounts for the current user.
    """
    account_service = AccountService(db)
    return account_service.get_active_by_user_id(user_id=user_id)

@router.get("/balance/total")
def read_total_balance(
    user_id: int,  # This will be replaced with actual auth mechanism
    currency: str = "USD",
    db: Session = Depends(get_db)
):
    """
    Get total balance across all active accounts for a specific currency.
    """
    account_service = AccountService(db)
    total_balance = account_service.get_total_balance(user_id=user_id, currency=currency)
    return {"total_balance": total_balance, "currency": currency}

@router.get("/{account_id}", response_model=Account)
def read_account(
    account_id: int,
    user_id: int,  # This will be replaced with actual auth mechanism
    db: Session = Depends(get_db)
):
    """
    Get a specific account by ID.
    """
    account_service = AccountService(db)
    account = account_service.get_by_id(account_id=account_id)
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
        
    # Verify user ownership
    if account.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
        
    return account

@router.put("/{account_id}", response_model=Account)
def update_account(
    account_id: int,
    account_in: AccountUpdate,
    user_id: int,  # This will be replaced with actual auth mechanism
    db: Session = Depends(get_db)
):
    """
    Update an account.
    """
    account_service = AccountService(db)
    
    # First get the account
    account = account_service.get_by_id(account_id=account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
        
    # Verify user ownership
    if account.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
        
    # Update the account
    updated_account = account_service.update(account_id=account_id, account_in=account_in)
    return updated_account

@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: int,
    user_id: int,  # This will be replaced with actual auth mechanism
    db: Session = Depends(get_db)
):
    """
    Delete an account.
    """
    account_service = AccountService(db)
    
    # First get the account
    account = account_service.get_by_id(account_id=account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
        
    # Verify user ownership
    if account.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
        
    # Delete the account
    account_service.delete(account_id=account_id)

@router.patch("/{account_id}/deactivate", response_model=Account)
def deactivate_account(
    account_id: int,
    user_id: int,  # This will be replaced with actual auth mechanism
    db: Session = Depends(get_db)
):
    """
    Deactivate an account.
    """
    account_service = AccountService(db)
    
    # First get the account
    account = account_service.get_by_id(account_id=account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
        
    # Verify user ownership
    if account.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
        
    # Deactivate the account
    return account_service.deactivate(account_id=account_id) 