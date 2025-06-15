import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from app.db.connection_and_session import get_db_session
from app.core.dependencies import get_current_user_id
from app.domains.credit_cards.schemas import CreditCardIn
from app.domains.credit_cards.service import (
    CreditCardService, 
    AccountNotFoundError, 
    AccountAccessDeniedError
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/")
def get_credit_cards():
    return {"message": "Hello, World!"}

@router.post("/", response_model=CreditCardIn, status_code=201)
def create_credit_card(
    credit_card_in: CreditCardIn, 
    db: Session = Depends(get_db_session), 
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Create a new credit card"""
    try:
        logger.info(f"Creating credit card for user {current_user_id}: {credit_card_in.name}")
        
        service = CreditCardService(db)
        result = service.create_credit_card(credit_card_in, current_user_id)
        
        logger.info(f"✅ Credit card created successfully: {result.id}")
        return result
        
    except AccountNotFoundError as e:
        logger.warning(f"❌ Account not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
        
    except AccountAccessDeniedError as e:
        logger.warning(f"❌ Access denied: {e}")
        raise HTTPException(status_code=403, detail="Access denied to this account")
        
    except Exception as e:
        logger.error(f"❌ Unexpected error creating credit card: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")