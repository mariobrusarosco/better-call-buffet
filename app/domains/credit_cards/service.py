from app.domains.credit_cards.models import CreditCard
from app.domains.credit_cards.schemas import CreditCardIn
from fastapi import HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from app.domains.accounts.models import Account
import logging

logger = logging.getLogger(__name__)

class CreditCardService:
    def __init__(self, db: Session):
        self.db = db

    def create_credit_card(self, credit_card_data: CreditCardIn, user_id: UUID) -> CreditCard:
        try:
            credit_card = CreditCard(**credit_card_data.model_dump())

            account = self.db.query(Account).filter(Account.id == credit_card_data.account_id).first()
            if not account:
                raise Exception("Account not found")

            if account.user_id != user_id:
                raise Exception("Forbidden")
            
            # Set broker_id from account and user_id
            credit_card.broker_id = account.broker_id
            credit_card.user_id = user_id

            self.db.add(credit_card)
            self.db.commit()
            self.db.refresh(credit_card)
            return credit_card
        except Exception as e:
            logger.error(f"Error in create_credit_card: {str(e)}")
            raise e

