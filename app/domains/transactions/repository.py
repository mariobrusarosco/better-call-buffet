from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, asc, desc
from sqlalchemy.orm import Session

from app.domains.transactions.models import Transaction
from app.domains.transactions.schemas import TransactionFilters


class TransactionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, transaction_data: dict):
        try:
            transaction = Transaction(**transaction_data)
            self.db.add(transaction)
            self.db.commit()
            self.db.refresh(transaction)
            return transaction
        except Exception as e:
            self.db.rollback()
            raise e

    def get_account_transactions_with_filters(
        self,
        account_id: UUID,
        user_id: UUID,
        filters: Optional[TransactionFilters] = None,
    ) -> Tuple[List[Transaction], int]:
        """
        Get account transactions using structured filters.

        Benefits:
        - ✅ Consistent filtering interface
        - ✅ Easy to extend with new filter options
        - ✅ Type-safe filter validation
        - ✅ Embedded pagination handling
        """
        # Base query
        query = self.db.query(Transaction).filter(
            and_(Transaction.account_id == account_id, Transaction.user_id == user_id)
        )

        # Apply structured filters
        if filters:
            query = self._apply_filters(query, filters)
            query = self._apply_sorting(query, filters)

            total_count = query.count()
            query = self._apply_pagination(query, filters)
        else:
            total_count = query.count()

        return query.all(), total_count

    def get_credit_card_transactions_with_filters(
        self,
        credit_card_id: UUID,
        user_id: UUID,
        filters: Optional[TransactionFilters] = None,
    ) -> Tuple[List[Transaction], int]:
        # Base query
        query = self.db.query(Transaction).filter(
            and_(
                Transaction.credit_card_id == credit_card_id,
                Transaction.user_id == user_id,
            )
        )

        # Apply structured filters
        if filters:
            query = self._apply_filters(query, filters)
            query = self._apply_sorting(query, filters)
            # Get total count before pagination
            total_count = query.count()

            # Apply pagination
            query = self._apply_pagination(query, filters)
        else:
            total_count = query.count()

        return query.all(), total_count

    def _apply_filters(self, query, filters: TransactionFilters):
        """🔧 Private method to build WHERE conditions dynamically"""
        # Date range filters
        if filters.date_from:
            query = query.filter(Transaction.date >= filters.date_from)
        if filters.date_to:
            query = query.filter(Transaction.date <= filters.date_to)

        # Content filters
        if filters.movement_type:
            query = query.filter(Transaction.movement_type == filters.movement_type)
        if filters.category:
            query = query.filter(Transaction.category.ilike(f"%{filters.category}%"))
        if filters.description_contains:
            query = query.filter(
                Transaction.description.ilike(f"%{filters.description_contains}%")
            )

        # Amount filters
        if filters.amount_min is not None:
            query = query.filter(Transaction.amount >= filters.amount_min)
        if filters.amount_max is not None:
            query = query.filter(Transaction.amount <= filters.amount_max)

        # Status filters
        if filters.is_paid is not None:
            query = query.filter(Transaction.is_paid == filters.is_paid)

        return query

    def _apply_sorting(self, query, filters: TransactionFilters):
        sort_fields = {
            "date": Transaction.date,
            "amount": Transaction.amount,
            "created_at": Transaction.created_at,
            "category": Transaction.category,
        }

        field = sort_fields.get(filters.sort_by or "date", Transaction.date)

        if filters.sort_order == "asc":
            query = query.order_by(asc(field))
        else:
            # Default to desc, with secondary sort by created_at desc
            query = query.order_by(desc(field), desc(Transaction.created_at))

        return query

    def _apply_pagination(self, query, filters: TransactionFilters):
        page = max(1, filters.page)
        per_page = min(100, max(1, filters.per_page))

        offset = (page - 1) * per_page
        return query.offset(offset).limit(per_page)
