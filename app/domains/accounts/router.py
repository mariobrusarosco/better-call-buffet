from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session
from app.domains.accounts.schemas import Account, AccountIn, AccountType
from app.domains.accounts.service import AccountService
from app.domains.statements.schemas import StatementIn, StatementResponse, StatementListResponse
from app.domains.statements.service import StatementService
from app.domains.transactions.schemas import TransactionFilters, TransactionListResponse
from app.domains.transactions.service import TransactionService

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


@router.get("/{account_id}/transactions", response_model=TransactionListResponse)
def get_account_transactions_endpoint(
    account_id: UUID,
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    date_from: Optional[datetime] = Query(
        None, description="Filter transactions from this date"
    ),
    date_to: Optional[datetime] = Query(
        None, description="Filter transactions to this date"
    ),
    movement_type: Optional[str] = Query(
        None, description="Filter by movement type (income/expense)"
    ),
    category: Optional[str] = Query(
        None, description="Filter by category (partial match)"
    ),
    description_contains: Optional[str] = Query(
        None, description="Filter by description (partial match)"
    ),
    amount_min: Optional[float] = Query(None, description="Filter by minimum amount"),
    amount_max: Optional[float] = Query(None, description="Filter by maximum amount"),
    is_paid: Optional[bool] = Query(None, description="Filter by payment status"),
    sort_by: Optional[str] = Query(
        "date", description="Sort field: date, amount, created_at, category"
    ),
    sort_order: Optional[str] = Query(
        "desc", description="Sort order: desc (newest first) or asc"
    ),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """
    🎓 Get paginated transactions for a specific account (STRUCTURED FILTERING PATTERN)

    This endpoint now uses the improved structured filtering approach:
    - Uses TransactionFilters internally for type safety and consistency
    - Maintains backward compatibility with existing API clients
    - Supports enhanced filtering capabilities like amount ranges and description search
    - Follows the same filtering pattern as credit card transactions

    Benefits:
    - ✅ Type-safe filter validation through Pydantic
    - ✅ Easy to extend with new filter options
    - ✅ Consistent filtering behavior across all transaction endpoints
    - ✅ Self-documenting filter capabilities
    - ✅ Enhanced filtering options (amount ranges, description search, payment status)
    """
    # First verify the account exists and belongs to the user
    account_service = AccountService(db)
    account = account_service.get_account_by_id(
        account_id=account_id, user_id=current_user_id
    )
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    try:
        transaction_filters = TransactionFilters(
            page=page,
            per_page=per_page,
            date_from=date_from,
            date_to=date_to,
            movement_type=movement_type,
            category=category,
            description_contains=description_contains,
            amount_min=amount_min,
            amount_max=amount_max,
            is_paid=is_paid,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        transaction_service = TransactionService(db)
        return transaction_service.get_account_transactions_with_filters(
            account_id=account_id,
            user_id=current_user_id,
            filters=transaction_filters,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving transactions: {str(e)}"
        )


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


@router.get("/{account_id}/statements", response_model=StatementListResponse)
def get_account_statements_endpoint(
    account_id: UUID,
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    is_processed: Optional[bool] = Query(None, description="Filter by processing status"),
    is_deleted: Optional[bool] = Query(False, description="Include deleted statements"),
    date_from: Optional[datetime] = Query(None, description="Filter from this date"),
    date_to: Optional[datetime] = Query(None, description="Filter to this date"),
    sort_by: Optional[str] = Query("created_at", description="Sort field"),
    sort_order: Optional[str] = Query("desc", description="Sort order: desc or asc"),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """
    Get paginated statements for a specific account.
    
    Can filter by processing status, date range, and more.
    """
    # First verify the account exists and belongs to the user
    account_service = AccountService(db)
    account = account_service.get_account_by_id(
        account_id=account_id, user_id=current_user_id
    )
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    try:
        from app.domains.statements.schemas import StatementFilters
        
        filters = StatementFilters(
            account_id=account_id,
            is_processed=is_processed,
            is_deleted=is_deleted,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            per_page=per_page,
        )

        statement_service = StatementService(db)
        return statement_service.get_account_statements_with_filters(
            account_id=account_id,
            user_id=current_user_id,
            filters=filters,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving statements: {str(e)}"
        )


@router.post("/{account_id}/statements", response_model=StatementResponse, status_code=201)
def create_account_statement_endpoint(
    account_id: UUID,
    statement_in: StatementIn,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """
    Create a new statement for a specific account.
    
    Processes raw statement data including transactions, balances, and due dates.
    The account_id from the URL path takes precedence over the one in the request body.
    """
    try:
        # Override account_id from path parameter to ensure consistency
        statement_in.account_id = account_id
        
        service = StatementService(db)
        statement = service.create_statement(statement_in, current_user_id)
        return StatementResponse.model_validate(statement)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error creating statement")
