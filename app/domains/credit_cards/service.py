from app.domains.credit_cards.models import CreditCard
from app.domains.credit_cards.schemas import CreditCardIn
from sqlalchemy.orm import Session
from uuid import UUID
from app.domains.accounts.models import Account

# Custom business exceptions
class AccountNotFoundError(Exception):
    pass

class AccountAccessDeniedError(Exception):
    pass

class CreditCardService:
    def __init__(self, db: Session):
        self.db = db

    def create_credit_card(self, credit_card_data: CreditCardIn, user_id: UUID) -> CreditCard:
        # Validate account exists and belongs to user
        account = self.db.query(Account).filter(Account.id == credit_card_data.account_id).first()
        if not account:
            raise AccountNotFoundError(f"Account {credit_card_data.account_id} not found")

        if account.user_id != user_id:
            raise AccountAccessDeniedError(f"User {user_id} does not own account {credit_card_data.account_id}")
        
        # Create credit card with proper relationships
        credit_card = CreditCard(**credit_card_data.model_dump())
        credit_card.broker_id = account.broker_id
        credit_card.user_id = user_id

        # Save to database
        self.db.add(credit_card)
        self.db.commit()
        self.db.refresh(credit_card)
        
        return credit_card

