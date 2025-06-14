from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.connection_and_session import get_db_session
from app.domains.credit_cards.schemas import CreditCardIn
from app.domains.credit_cards.service import CreditCardService


router = APIRouter()

@router.get("/")
def get_credit_cards():
    return {"message": "Hello, World!"}

@router.post("/", response_model=CreditCardIn, status_code=201)
def create_credit_card(credit_card_in: CreditCardIn, db: Session = Depends(get_db_session)):
    credit_card_service = CreditCardService(db)

    return credit_card_service.create_credit_card(credit_card_in)