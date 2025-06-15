from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from app.db.connection_and_session import get_db_session
from app.core.dependencies import get_current_user_id
from app.domains.credit_cards.schemas import CreditCardIn
from app.domains.credit_cards.service import CreditCardService

router = APIRouter()

@router.get("/")
def get_credit_cards():
    return {"message": "Hello, World!"}

@router.post("/", response_model=CreditCardIn, status_code=201)
def create_credit_card(credit_card_in: CreditCardIn, db: Session = Depends(get_db_session), current_user_id: UUID = Depends(get_current_user_id)):
    try:
        credit_card_service = CreditCardService(db)
        return credit_card_service.create_credit_card(credit_card_in, current_user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating credit card: {e}")