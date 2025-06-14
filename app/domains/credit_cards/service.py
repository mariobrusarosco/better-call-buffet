from app.domains.credit_cards.models import CreditCard
from app.domains.credit_cards.schemas import CreditCardIn
from fastapi import HTTPException
from sqlalchemy.orm import Session


class CreditCardService:
    def __init__(self, db: Session):
        self.db = db

    def create_credit_card(self, credit_card_data: CreditCardIn) -> CreditCard:
        try:
            credit_card = CreditCard(**credit_card_data.model_dump())
            self.db.add(credit_card)
            self.db.commit()
            self.db.refresh(credit_card)
            return credit_card
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Error creating credit card: {e}")

