import logging
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
    InvoiceIn,
    InvoiceListResponse,
    PaginationMeta,
)
from app.domains.invoices.service import InvoiceService

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


@router.get("/{credit_card_id}/invoices", response_model=InvoiceListResponse)
def get_invoices(
    credit_card_id: UUID,
    page: int = Query(1, description="Page number", ge=1),
    per_page: int = Query(10, description="Items per page", ge=1, le=100),
    include_deleted: bool = Query(False, description="Include soft-deleted invoices"),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get all invoices for a specific credit card with pagination"""
    service = InvoiceService(db)

    # Get paginated invoices
    invoices = service.get_invoices_by_credit_card(
        credit_card_id, current_user_id, include_deleted, page, per_page
    )

    # Get total count for pagination metadata (simple approach: get all without pagination)
    all_invoices = service.get_invoices_by_credit_card(
        credit_card_id,
        current_user_id,
        include_deleted,
        1,
        999999,  # Large number to get all
    )
    total_count = len(all_invoices)

    # Calculate pagination metadata
    total_pages = (total_count + per_page - 1) // per_page
    has_next = page < total_pages
    has_previous = page > 1

    return InvoiceListResponse(
        data=[Invoice.model_validate(invoice) for invoice in invoices],
        meta=PaginationMeta(
            has_next=has_next,
            has_previous=has_previous,
            page=page,
            per_page=per_page,
            total=total_count,
        ),
    )
