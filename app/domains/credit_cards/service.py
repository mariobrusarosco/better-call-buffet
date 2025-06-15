from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.domains.accounts.models import Account
from app.domains.credit_cards.models import CreditCard
from app.domains.credit_cards.repository import CreditCardRepository
from app.domains.credit_cards.schemas import CreditCardFilters, CreditCardIn


# Custom business exceptions
class AccountNotFoundError(Exception):
    """Raised when account doesn't exist"""

    pass


class AccountAccessDeniedError(Exception):
    """Raised when user doesn't own the account"""

    pass


class CreditCardService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = CreditCardRepository(db)

    def get_user_credit_cards_filtered(
        self, user_id: UUID, filters: Optional[CreditCardFilters] = None
    ) -> List[CreditCard]:
        # Set default filters if none provided
        if filters is None:
            filters = CreditCardFilters(
                is_deleted=False
            )  # Don't show deleted by default

        return self.repository.get_user_credit_cards_with_filters(user_id, filters)

    def create_credit_card(
        self, credit_card_data: CreditCardIn, user_id: UUID
    ) -> CreditCard:
        account = (
            self.db.query(Account)
            .filter(Account.id == credit_card_data.account_id)
            .first()
        )
        if not account:
            raise AccountNotFoundError(
                f"Account {credit_card_data.account_id} not found"
            )

        if account.user_id != user_id:
            raise AccountAccessDeniedError(
                f"User {user_id} does not own account {credit_card_data.account_id}"
            )

        credit_card = CreditCard(**credit_card_data.model_dump())
        credit_card.broker_id = account.broker_id
        credit_card.user_id = user_id

        self.db.add(credit_card)
        self.db.commit()
        self.db.refresh(credit_card)

        return credit_card
