from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session
from app.domains.transactions.schemas import (
    TransactionBulkDeleteRequest,
    TransactionBulkRequest,
    TransactionBulkResponse,
    TransactionBulkUpdate,
    TransactionBulkUpdateResponse,
    TransactionFilters,
    TransactionIn,
    TransactionListResponse,
    TransactionResponse,
    TransactionUpdate,
)
from app.domains.transactions.service import TransactionService

router = APIRouter()


def _parse_uuid_list(values: Optional[List[str]]) -> Optional[List[UUID]]:
    if not values:
        return None
    parsed = []
    for value in values:
        for raw_uuid in value.split(","):
            try:
                parsed.append(UUID(raw_uuid.strip()))
            except ValueError as exc:
                from fastapi import HTTPException

                raise HTTPException(
                    status_code=422, detail=f"Invalid UUID format: {raw_uuid}"
                ) from exc
    return parsed


@router.get("", response_model=TransactionListResponse)
def get_user_transactions(
    # Pagination parameters
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    # Date range filters
    date_from: Optional[datetime] = Query(
        None, description="Filter transactions from this date"
    ),
    date_to: Optional[datetime] = Query(
        None, description="Filter transactions to this date"
    ),
    # Content filters
    movement_type: Optional[List[str]] = Query(
        None, description="Filter by movement type (e.g., income, expense)"
    ),
    tag_ids: Optional[List[str]] = Query(
        None,
        description="Required tag IDs (comma-separated or repeated)",
    ),
    exclude_tag_ids: Optional[List[str]] = Query(
        None,
        description="Excluded tag IDs (comma-separated or repeated)",
    ),
    tag_match: Literal["all", "any"] = Query("all"),
    description_contains: Optional[str] = Query(
        None, description="Filter by description (partial match)"
    ),
    # Amount filters
    amount_min: Optional[float] = Query(None, description="Filter by minimum amount"),
    amount_max: Optional[float] = Query(None, description="Filter by maximum amount"),
    # Status filters
    is_paid: Optional[bool] = Query(None, description="Filter by payment status"),
    # Vendor & Subscription filters
    vendor_id: Optional[UUID] = Query(None, description="Filter by vendor"),
    subscription_id: Optional[UUID] = Query(None, description="Filter by subscription"),
    # Sorting options
    sort_by: Optional[str] = Query(
        "date", description="Sort field: date, amount, created_at"
    ),
    sort_order: Optional[str] = Query(
        "desc", description="Sort order: desc (newest first) or asc"
    ),
    # Dependencies
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    🎯 Get all user transactions with comprehensive filtering and pagination

    This endpoint provides access to ALL user transactions across accounts and credit cards.

    Benefits:
    - ✅ Single endpoint for all user financial data
    - ✅ Comprehensive filtering by date, amount, tags, type, etc.
    - ✅ Consistent pagination across all transaction endpoints
    - ✅ Flexible sorting options
    - ✅ Type-safe query parameter validation

    Use Cases:
    - Display user's complete transaction history
    - Financial analytics and reporting
    - Search and filter transactions
    - Export transaction data
    """
    # Handle comma-separated values for movement_type if passed as a single string in a list
    # Example: ?movement_type=income,expense -> ["income,expense"] -> ["income", "expense"]
    final_movement_type = None
    if movement_type:
        final_movement_type = []
        for mt in movement_type:
            final_movement_type.extend([t.strip() for t in mt.split(",")])

    # Create structured filters from query parameters
    filters = TransactionFilters(
        page=page,
        per_page=per_page,
        date_from=date_from,
        date_to=date_to,
        movement_type=final_movement_type,
        tag_ids=_parse_uuid_list(tag_ids),
        exclude_tag_ids=_parse_uuid_list(exclude_tag_ids),
        tag_match=tag_match,
        description_contains=description_contains,
        amount_min=amount_min,
        amount_max=amount_max,
        is_paid=is_paid,
        vendor_id=vendor_id,
        subscription_id=subscription_id,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # Get transactions using the new service method
    service = TransactionService(db)
    return service.get_user_transactions_with_filters(user_id, filters)


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction_by_id_endpoint(
    transaction_id: UUID,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    service = TransactionService(db)
    return service.get_account_transaction_by_id(transaction_id, user_id)


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
    deleted_count = service.bulk_delete_transactions(
        bulk_delete_request.transaction_ids, user_id
    )

    return {
        "message": f"Successfully deleted {deleted_count} transactions",
        "deleted_count": deleted_count,
        "requested_count": len(bulk_delete_request.transaction_ids),
    }


@router.patch("/bulk", response_model=TransactionBulkUpdateResponse)
def update_transactions_bulk_endpoint(
    bulk_update: TransactionBulkUpdate,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """Apply the same partial update atomically to selected transactions."""
    service = TransactionService(db)
    return service.update_transactions_bulk(bulk_update, user_id)


@router.patch("/{transaction_id}", response_model=TransactionResponse)
def update_transaction_endpoint(
    transaction_id: UUID,
    update_data: TransactionUpdate,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    ✏️ Update an existing transaction (PATCH - partial update)

    Update one or more fields of an existing transaction.
    Only include the fields you want to change in the request body.

    Benefits:
    - ✅ Flexible partial updates (update only what you need)
    - ✅ User ownership validation
    - ✅ Account/card ownership validation
    - ✅ XOR constraint enforcement
    - ✅ Clear error messages

    Use Cases:
    - Fix incorrect transaction amount
    - Update transaction description
    - Replace transaction tags
    - Mark transaction as paid/unpaid
    - Move transaction to different account/card

    Request Body Examples:

    1. Update description only:
    {
        "description": "Groceries from Whole Foods"
    }

    2. Update amount and tags:
    {
        "amount": 150.00,
        "tag_ids": ["tag-uuid"]
    }

    3. Switch from account to credit card:
    {
        "account_id": null,
        "credit_card_id": "f9e8d7c6-5432-10ab-cdef-0987654321ba"
    }

    Validation:
    - Transaction must exist and belong to user (404 if not)
    - If changing account_id, user must own the new account (404 if not)
    - If changing credit_card_id, user must own the new card (404 if not)
    - Must maintain XOR constraint: account XOR credit card (400 if violated)
    - Amount must be positive (422 if not)
    - Movement type must be "income" or "expense" (422 if not)
    """
    service = TransactionService(db)
    return service.update_transaction(transaction_id, user_id, update_data)


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

        raise HTTPException(
            status_code=404, detail="Transaction not found or not accessible"
        )

    return {"message": "Transaction deleted successfully"}
