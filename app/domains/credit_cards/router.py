import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional, List
from app.db.connection_and_session import get_db_session
from app.core.dependencies import get_current_user_id
from app.domains.credit_cards.schemas import (
    CreditCardIn,
    CreditCardResponse,
    CreditCardListResponse,
    CreditCardListMeta,
    CreditCardFilters
)
from app.domains.credit_cards.service import (
    CreditCardService, 
    AccountNotFoundError, 
    AccountAccessDeniedError
)
from app.domains.credit_cards.models import CreditCard

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/{account_id}", response_model=CreditCardListResponse)
def get_credit_cards(
    # 🎯 Professional API Design: Multiple query parameters
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_deleted: Optional[bool] = Query(False, description="Include deleted cards"),
    account_id: Optional[UUID] = Query(None, description="Filter by account ID"),
    card_brand: Optional[str] = Query(None, description="Filter by card brand (partial match)"),
    name_contains: Optional[str] = Query(None, description="Filter by name (partial match)"),
    due_date_month: Optional[int] = Query(None, description="Filter by due date month (1-12)"),
    sort_by: Optional[str] = Query("name", description="Sort field: name, balance, due_date, created_at"),
    sort_order: Optional[str] = Query("asc", description="Sort order: asc, desc"),
    
    # Dependencies
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Examples:
    - GET /credit_cards/ → All cards
    - GET /credit_cards/?is_active=true → Active cards only  
    - GET /credit_cards/?card_brand=visa&min_balance=1000 → Visa cards with balance > 1000
    - GET /credit_cards/?sort_by=balance&sort_order=desc → Sorted by balance descending
    """
    try:
        filters = CreditCardFilters(
            is_active=is_active,
            is_deleted=is_deleted,
            account_id=account_id,
            card_brand=card_brand,
            name_contains=name_contains,
            due_date_month=due_date_month,
            sort_by=sort_by,
            sort_order=sort_order
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
                has_previous=False
            )
        )
        
    except Exception as e:
        logger.error(f"❌ Error retrieving credit cards: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving credit cards")

@router.post("/", response_model=CreditCardResponse, status_code=201)
def create_credit_card(
    credit_card_in: CreditCardIn, 
    db: Session = Depends(get_db_session), 
    current_user_id: UUID = Depends(get_current_user_id)
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