"""
Credit Card Repository - Database Access Layer

Repository Pattern Benefits:
- Encapsulates database queries
- Easy to test (can mock repository)
- Consistent query interface
- Database-agnostic (can switch from SQLAlchemy to MongoDB)
- Follows Single Responsibility Principle
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import asc, desc, extract
from sqlalchemy.orm import Session

from app.domains.accounts.models import Account
from app.domains.credit_cards.models import CreditCard
from app.domains.credit_cards.schemas import CreditCardFilters
from app.domains.invoices.models import Invoice


class CreditCardRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_credit_cards_with_filters(
        self, user_id: UUID, filters: Optional[CreditCardFilters] = None
    ) -> List[CreditCard]:
        # Start with base query
        query = self.db.query(CreditCard).filter(CreditCard.user_id == user_id)
        # Apply filters if provided
        if filters:
            query = self._apply_filters(query, filters)
            query = self._apply_sorting(query, filters)

        return query.all()

    def get_user_unique_credit_card_with_filters(
        self, user_id: UUID, filters: Optional[CreditCardFilters] = None
    ) -> Optional[CreditCard]:
        query = self.db.query(CreditCard).filter(CreditCard.user_id == user_id)
        if filters:
            query = self._apply_filters(query, filters)
        return query.first()

    def _apply_filters(self, query, filters: CreditCardFilters):
        """🔧 Private method to build WHERE conditions dynamically"""
        # Boolean filters
        if filters.is_active is not None:
            query = query.filter(CreditCard.is_active == filters.is_active)
        if filters.is_deleted is not None:
            query = query.filter(CreditCard.is_deleted == filters.is_deleted)
        # UUID filters
        if filters.account_id:
            query = query.filter(CreditCard.account_id == filters.account_id)
        if filters.credit_card_id:
            query = query.filter(CreditCard.id == filters.credit_card_id)
        # String filters
        if filters.card_brand:
            query = query.filter(CreditCard.brand.ilike(f"%{filters.card_brand}%"))
        if filters.name_contains:
            query = query.filter(CreditCard.name.ilike(f"%{filters.name_contains}%"))
        if filters.due_date_month:
            # Extract month from due_date and compare
            query = query.filter(
                extract("month", CreditCard.due_date) == filters.due_date_month
            )

        return query

    def _apply_sorting(self, query, filters: CreditCardFilters):
        sort_fields = {
            "name": CreditCard.name,
            "due_date": CreditCard.due_date,
            "created_at": CreditCard.created_at,
        }

        field = sort_fields.get(filters.sort_by or "name", CreditCard.name)

        if filters.sort_order == "desc":
            query = query.order_by(desc(field))
        else:
            query = query.order_by(asc(field))

        return query

    def create_credit_card(self, credit_card: CreditCard) -> CreditCard:
        """Create a new credit card"""
        self.db.add(credit_card)
        self.db.commit()
        self.db.refresh(credit_card)
        return credit_card
