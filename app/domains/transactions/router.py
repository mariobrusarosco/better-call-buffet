from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session
from app.domains.transactions.schemas import (
    TransactionBulkDeleteRequest,
    TransactionBulkRequest,
    TransactionBulkResponse,
    TransactionFilters,
    TransactionIn,
    TransactionListResponse,
    TransactionResponse,
)
from app.domains.transactions.service import TransactionService

router = APIRouter()


@router.get("", response_model=TransactionListResponse)
def get_user_transactions(
    # Pagination parameters
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    
    # Date range filters
    date_from: Optional[datetime] = Query(None, description="Filter transactions from this date"),
    date_to: Optional[datetime] = Query(None, description="Filter transactions to this date"),
    
    # Content filters
    movement_type: Optional[str] = Query(None, description="Filter by movement type: income or expense"),
    category: Optional[str] = Query(None, description="Filter by category (partial match)"),
    description_contains: Optional[str] = Query(None, description="Filter by description (partial match)"),
    
    # Amount filters
    amount_min: Optional[float] = Query(None, description="Filter by minimum amount"),
    amount_max: Optional[float] = Query(None, description="Filter by maximum amount"),
    
    # Status filters
    is_paid: Optional[bool] = Query(None, description="Filter by payment status"),
    
    # Sorting options
    sort_by: Optional[str] = Query("date", description="Sort field: date, amount, created_at, category"),
    sort_order: Optional[str] = Query("desc", description="Sort order: desc (newest first) or asc"),
    
    # Dependencies
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    🎯 Get all user transactions with comprehensive filtering and pagination
    
    This endpoint provides access to ALL user transactions across accounts and credit cards.
    
    Benefits:
    - ✅ Single endpoint for all user financial data
    - ✅ Comprehensive filtering by date, amount, category, type, etc.
    - ✅ Consistent pagination across all transaction endpoints
    - ✅ Flexible sorting options
    - ✅ Type-safe query parameter validation
    
    Use Cases:
    - Display user's complete transaction history
    - Financial analytics and reporting
    - Search and filter transactions
    - Export transaction data
    """
    # Create structured filters from query parameters
    filters = TransactionFilters(
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
    
    # Get transactions using the new service method
    service = TransactionService(db)
    return service.get_user_transactions_with_filters(user_id, filters)


@router.post("", response_model=TransactionResponse)
def create_transaction_endpoint(
    transaction: TransactionIn,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    service = TransactionService(db)
    service.check_transaction_validity(
        transaction.account_id or UUID(int=0),
        transaction.credit_card_id or UUID(int=0),
        user_id,
    )

    return service.create_transaction(transaction, user_id)


@router.post("/bulk", response_model=TransactionBulkResponse)
def create_transactions_bulk_endpoint(
    bulk_request: TransactionBulkRequest,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Create multiple transactions in a single request.
    
    Returns detailed success/failure status for each transaction.
    Validates account/credit card ownership and XOR constraints.
    """
    service = TransactionService(db)
    return service.create_transactions_bulk_with_validation(bulk_request, user_id)


@router.delete("/bulk")
def delete_transactions_bulk_endpoint(
    bulk_delete_request: TransactionBulkDeleteRequest,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    🗑️ Bulk delete multiple transactions
    
    This endpoint allows users to delete multiple transactions in a single request.
    
    Benefits:
    - ✅ User ownership validation for all transactions
    - ✅ High performance bulk delete
    - ✅ Single database round-trip
    - ✅ Returns count of deleted transactions
    
    Use Cases:
    - Remove multiple incorrect transactions
    - Clean up duplicate entries
    - Bulk transaction cleanup
    
    Request Body:
    {
        "transaction_ids": ["uuid1", "uuid2", "uuid3"]
    }
    """
    service = TransactionService(db)
    deleted_count = service.bulk_delete_transactions(bulk_delete_request.transaction_ids, user_id)
    
    return {
        "message": f"Successfully deleted {deleted_count} transactions",
        "deleted_count": deleted_count,
        "requested_count": len(bulk_delete_request.transaction_ids)
    }


@router.delete("/{transaction_id}")
def delete_transaction_endpoint(
    transaction_id: UUID,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    🗑️ Delete a single transaction by ID
    
    This endpoint allows users to delete their own transactions.
    
    Benefits:
    - ✅ User ownership validation
    - ✅ Safe deletion with rollback
    - ✅ Audit logging
    - ✅ Returns success status
    
    Use Cases:
    - Remove incorrect transactions
    - Clean up duplicate entries
    - User-initiated transaction removal
    """
    service = TransactionService(db)
    success = service.delete_transaction(transaction_id, user_id)
    
    if not success:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Transaction not found or not accessible")
    
    return {"message": "Transaction deleted successfully"}