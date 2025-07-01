import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session
from app.domains.credit_cards.models import CreditCard
from app.domains.credit_cards.schemas import (
    CreditCardFilters,
    CreditCardIn,
    CreditCardListMeta,
    CreditCardListResponse,
    CreditCardResponse,
)
from app.domains.credit_cards.service import (
    AccountAccessDeniedError,
    AccountNotFoundError,
    CreditCardService,
)
from app.domains.invoices.schemas import (
    Invoice,
    InvoiceFilters,
    InvoiceIn,
    InvoiceListResponse,
    PaginationMeta,
)
from app.domains.invoices.service import InvoiceService
from app.domains.transactions.schemas import TransactionFilters, TransactionListResponse
from app.domains.transactions.service import TransactionService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{credit_card_id}", response_model=CreditCardResponse)
def get_credit_card_by_id(
    credit_card_id: UUID,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """
    🎓 Single Credit Card Retrieval Using Filtering System

    This demonstrates how to use the same filtering infrastructure
    for single-item retrieval by filtering on credit_card_id.
    """
    try:
        service = CreditCardService(db)
        filters = CreditCardFilters(credit_card_id=credit_card_id)

        # Use the same filtering method but expect a single result
        credit_cards = service.get_user_unique_credit_card_with_filters(
            current_user_id, filters
        )

        if not credit_cards:
            raise HTTPException(
                status_code=404, detail=f"Credit card {credit_card_id} not found"
            )

        # Return the first (and should be only) result
        return CreditCardResponse.model_validate(credit_cards)

    except HTTPException:
        # Re-raise HTTP exceptions (like 404)
        raise
    except Exception as e:
        logger.error(f"❌ Error retrieving credit card {credit_card_id}: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving credit card")


@router.get("", response_model=CreditCardListResponse)
def get_credit_cards_endpoint(
    account_id: Optional[UUID] = Query(
        None, description="Account ID (required for filtering)"
    ),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_deleted: Optional[bool] = Query(False, description="Include deleted cards"),
    card_brand: Optional[str] = Query(
        None, description="Filter by card brand (partial match)"
    ),
    name_contains: Optional[str] = Query(
        None, description="Filter by name (partial match)"
    ),
    due_date_month: Optional[int] = Query(
        None, description="Filter by due date month (1-12)"
    ),
    sort_by: Optional[str] = Query(
        "name", description="Sort field: name, balance, due_date, created_at"
    ),
    sort_order: Optional[str] = Query("asc", description="Sort order: asc, desc"),
    # Dependencies
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """
    🎓 Flexible Credit Card Filtering (REUSABLE STRATEGY)

    This endpoint demonstrates the power of reusable filtering logic.
    The same underlying method handles ALL filtering scenarios.

    Examples:
    - GET /credit_cards?account_id=uuid → Cards for specific account
    - GET /credit_cards?account_id=uuid&is_active=true → Active cards only
    - GET /credit_cards?account_id=uuid&card_brand=visa → Visa cards
    - GET /credit_cards?account_id=uuid&sort_by=due_date&sort_order=desc → Sorted

    Benefits:
    - ✅ Single filtering method handles all scenarios
    - ✅ Consistent security (user-level filtering always applied)
    - ✅ Easy to extend (just add new filter parameters)
    - ✅ Same performance optimizations everywhere
    """
    try:
        # For now, require account_id (can be made optional later for "all cards" scenarios)
        if not account_id:
            raise HTTPException(
                status_code=400,
                detail="account_id is required for filtering credit cards",
            )

        filters = CreditCardFilters(
            is_active=is_active,
            is_deleted=is_deleted,
            account_id=account_id,
            card_brand=card_brand,
            name_contains=name_contains,
            due_date_month=due_date_month,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        service = CreditCardService(db)

        credit_cards = service.get_user_credit_cards_filtered(current_user_id, filters)

        return CreditCardListResponse(
            data=[CreditCardResponse.model_validate(card) for card in credit_cards],
            meta=CreditCardListMeta(
                total=len(credit_cards),
                page=1,
                per_page=len(credit_cards),  # No pagination yet
                has_next=False,
                has_previous=False,
            ),
        )

    except Exception as e:
        logger.error(f"❌ Error retrieving credit cards: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving credit cards")


@router.post("/", response_model=CreditCardResponse, status_code=201)
def create_credit_card(
    credit_card_in: CreditCardIn,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    try:
        service = CreditCardService(db)
        result = service.create_credit_card(credit_card_in, current_user_id)

        return CreditCardResponse.model_validate(result)

    except AccountNotFoundError as e:
        logger.warning(f"❌ Account not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))

    except AccountAccessDeniedError as e:
        logger.warning(f"❌ Access denied: {e}")
        raise HTTPException(status_code=403, detail="Access denied to this account")

    except Exception as e:
        logger.error(f"❌ Unexpected error creating credit card: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{credit_card_id}/invoices", response_model=Invoice, status_code=201)
def create_invoice(
    invoice_in: InvoiceIn,
    credit_card_id: UUID = Path(..., description="The ID of the credit card"),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """
    🎓 Create a new invoice for a specific credit card (NESTED RESOURCE PATTERN)

    This endpoint demonstrates RESTful nested resource design:
    - POST /credit_cards/{id}/invoices creates an invoice FOR that credit card
    - The credit_card_id comes from the URL path (not request body)
    - Validates credit card ownership before creating invoice

    Benefits:
    - ✅ Clear resource hierarchy
    - ✅ Intuitive URL structure
    - ✅ Automatic credit card validation
    - ✅ Consistent with GET /credit_cards/{id}/invoices
    """
    try:
        service = InvoiceService(db)

        # Override credit_card_id from path parameter
        invoice_data = invoice_in.model_dump()
        invoice_data["credit_card_id"] = credit_card_id

        # Validate that path parameter matches body (if provided)
        if invoice_in.credit_card_id != credit_card_id:
            raise HTTPException(
                status_code=400,
                detail="Credit card ID in path must match credit card ID in request body",
            )

        # Create invoice using the existing service
        created_invoice = service.create_invoice(
            invoice_in=InvoiceIn(**invoice_data), user_id=current_user_id
        )

        logger.info(f"✅ Invoice created successfully for credit card {credit_card_id}")
        return Invoice.model_validate(created_invoice)

    except ValueError as e:
        logger.warning(f"❌ Validation error creating invoice: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Unexpected error creating invoice: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{credit_card_id}/invoices", response_model=InvoiceListResponse)
def get_invoices(
    credit_card_id: UUID,
    # 🎓 STRUCTURED FILTERING PARAMETERS
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page (max 100)"),
    # Status filters
    is_paid: Optional[bool] = Query(None, description="Filter by payment status"),
    is_deleted: Optional[bool] = Query(False, description="Include deleted invoices"),
    # Date filters
    date_from: Optional[datetime] = Query(
        None, description="Filter invoices from this date"
    ),
    date_to: Optional[datetime] = Query(
        None, description="Filter invoices to this date"
    ),
    # Amount filters
    amount_min: Optional[float] = Query(None, description="Filter by minimum amount"),
    amount_max: Optional[float] = Query(None, description="Filter by maximum amount"),
    # Period filter
    period_contains: Optional[str] = Query(
        None, description="Filter by period (partial match)"
    ),
    # Sorting options
    sort_by: Optional[str] = Query(
        "created_at", description="Sort field: created_at, updated_at, is_paid"
    ),
    sort_order: Optional[str] = Query(
        "desc", description="Sort order: desc (newest first) or asc"
    ),
    # Dependencies
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """
    🎓 Get paginated invoices for a specific credit card (STRUCTURED FILTERING PATTERN)

    This endpoint now uses the improved structured filtering approach:
    - Uses InvoiceFilters internally for type safety and consistency
    - Maintains backward compatibility with existing API clients
    - Supports enhanced filtering capabilities like amount ranges and period search
    - Follows the same filtering pattern as transaction endpoints

    Benefits:
    - ✅ Type-safe filter validation through Pydantic
    - ✅ Easy to extend with new filter options
    - ✅ Consistent filtering behavior across all endpoints
    - ✅ Self-documenting filter capabilities
    - ✅ Enhanced filtering options (amount ranges, period search, payment status)

    Enhanced filtering capabilities:
    - Date range (date_from, date_to)
    - Payment status (is_paid)
    - Deletion status (is_deleted)
    - Amount range (amount_min, amount_max) - NEW!
    - Period search (period_contains) - NEW!
    - Flexible sorting options - ENHANCED!
    """
    # Create structured filters from query parameters
    invoice_filters = InvoiceFilters(
        credit_card_id=credit_card_id,
        page=page,
        per_page=per_page,
        is_paid=is_paid,
        is_deleted=is_deleted,
        date_from=date_from,
        date_to=date_to,
        amount_min=amount_min,
        amount_max=amount_max,
        period_contains=period_contains,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # Get invoices using the new structured filtering method
    service = InvoiceService(db)
    try:
        return service.get_credit_card_invoices_with_filters(
            credit_card_id=credit_card_id,
            user_id=current_user_id,
            filters=invoice_filters,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error retrieving invoices")


@router.get("/{credit_card_id}/transactions", response_model=TransactionListResponse)
def get_credit_card_transactions_endpoint(
    credit_card_id: UUID,
    # 🎓 STRUCTURED FILTERING PARAMETERS
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    # Date filters
    date_from: Optional[datetime] = Query(
        None, description="Filter transactions from this date"
    ),
    date_to: Optional[datetime] = Query(
        None, description="Filter transactions to this date"
    ),
    # Content filters
    movement_type: Optional[str] = Query(
        None, description="Filter by movement type (income/expense)"
    ),
    category: Optional[str] = Query(
        None, description="Filter by category (partial match)"
    ),
    description_contains: Optional[str] = Query(
        None, description="Filter by description (partial match)"
    ),
    # Amount filters
    amount_min: Optional[float] = Query(None, description="Filter by minimum amount"),
    amount_max: Optional[float] = Query(None, description="Filter by maximum amount"),
    # Status filters
    is_paid: Optional[bool] = Query(None, description="Filter by payment status"),
    # Sorting options
    sort_by: Optional[str] = Query(
        "date", description="Sort field: date, amount, created_at, category"
    ),
    sort_order: Optional[str] = Query(
        "desc", description="Sort order: desc (newest first) or asc"
    ),
    # Dependencies
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """
    🎓 Get paginated transactions for a specific credit card (STRUCTURED FILTERING PATTERN)

    This endpoint now demonstrates the improved structured filtering approach:
    - Uses TransactionFilters internally for type safety and consistency
    - Maintains backward compatibility with existing API clients
    - Supports enhanced filtering capabilities like amount ranges and description search
    - Follows the same filtering pattern as other domain endpoints

    Benefits:
    - ✅ Type-safe filter validation through Pydantic
    - ✅ Easy to extend with new filter options
    - ✅ Consistent filtering behavior across all transaction endpoints
    - ✅ Self-documenting filter capabilities
    - ✅ Enhanced filtering options (amount ranges, description search, payment status)

    Enhanced filtering capabilities:
    - Date range (date_from, date_to)
    - Movement type (income/expense)
    - Category (partial text match)
    - Description (partial text match) - NEW!
    - Amount range (amount_min, amount_max) - NEW!
    - Payment status (is_paid) - NEW!
    - Flexible sorting options - ENHANCED!
    """
    # First verify the credit card exists and belongs to the user
    credit_card_service = CreditCardService(db)
    try:
        card_filters = CreditCardFilters(credit_card_id=credit_card_id)
        credit_card = credit_card_service.get_user_unique_credit_card_with_filters(
            current_user_id, card_filters
        )
        if not credit_card:
            raise HTTPException(status_code=404, detail="Credit card not found")
    except Exception as e:
        logger.error(f"❌ Error validating credit card {credit_card_id}: {e}")
        raise HTTPException(status_code=404, detail="Credit card not found")

    # Create structured filters from query parameters
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

    # Get transactions using the new structured filtering method
    transaction_service = TransactionService(db)
    try:
        return transaction_service.get_credit_card_transactions_with_filters(
            credit_card_id=credit_card_id,
            user_id=current_user_id,
            filters=transaction_filters,
        )
    except Exception as e:
        logger.error(
            f"❌ Error retrieving transactions for credit card {credit_card_id}: {e}"
        )
        raise HTTPException(
            status_code=500, detail=f"Error retrieving transactions: {str(e)}"
        )
