from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, asc, desc, or_
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

    def bulk_create(self, transactions_data: List[dict]) -> List[UUID]:
        """
        Bulk insert transactions with repository pattern consistency.
        
        Benefits:
        - ✅ Maintains repository abstraction layer
        - ✅ High performance bulk insert via SQLAlchemy
        - ✅ Single database round-trip
        - ✅ Consistent error handling with rollback
        - ✅ Returns list of created transaction IDs
        
        Args:
            transactions_data: List of dictionaries containing transaction data
            
        Returns:
            List of UUIDs for the created transactions
            
        Raises:
            Exception: If bulk insert fails, rolls back transaction
        """
        try:
            self.db.bulk_insert_mappings(Transaction, transactions_data)
            self.db.commit()
            return [tx_data["id"] for tx_data in transactions_data]
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

    def get_account_and_related_credit_card_transactions_with_filters(
        self,
        account_id: UUID,
        user_id: UUID,
        filters: Optional[TransactionFilters] = None,
    ) -> Tuple[List[Transaction], int]:
        """
        🎓 ENHANCED: Get account transactions AND credit card transactions for cards linked to the account.
        
        This method provides a unified view of all financial activity related to an account:
        - Direct account transactions (account_id = account_id)
        - Credit card transactions where credit_card belongs to this account
        
        Benefits:
        - ✅ Complete financial picture for account
        - ✅ Unified transaction history
        - ✅ Same filtering and pagination interface
        - ✅ Better user experience
        """
        from app.domains.credit_cards.models import CreditCard
        
        # Base query for account transactions OR credit card transactions linked to this account
        query = self.db.query(Transaction).filter(
            and_(
                Transaction.user_id == user_id,  # Always ensure user owns transactions
                or_(
                    # Direct account transactions
                    Transaction.account_id == account_id,
                    # Credit card transactions where the card belongs to this account
                    Transaction.credit_card_id.in_(
                        self.db.query(CreditCard.id)
                        .filter(and_(
                            CreditCard.account_id == account_id,
                            CreditCard.user_id == user_id,
                            CreditCard.is_active == True,
                            CreditCard.is_deleted == False
                        ))
                        .subquery()
                    )
                )
            )
        )

        # Apply structured filters (same as before)
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

    def get_user_transactions_with_filters(
        self,
        user_id: UUID,
        filters: Optional[TransactionFilters] = None,
    ) -> Tuple[List[Transaction], int]:
        """
        Get all user transactions (from accounts and credit cards) using structured filters.

        Benefits:
        - ✅ Single endpoint for all user transactions
        - ✅ Consistent filtering interface across domains
        - ✅ Type-safe filter validation
        - ✅ Embedded pagination handling
        """
        # Base query for all user transactions
        query = self.db.query(Transaction).filter(
            Transaction.user_id == user_id
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

    def get_account_transactions_since_timestamp(
        self, account_id: UUID, user_id: UUID, since_timestamp: datetime
    ) -> List[Transaction]:
        """
        Get all account transactions created after a specific timestamp.
        
        This method is optimized for balance calculation performance:
        - Returns only transactions created after the given timestamp
        - No pagination or complex filtering
        - Ordered by created_at for consistent processing
        
        Args:
            account_id: ID of the account
            user_id: ID of the user (for security)
            since_timestamp: Only return transactions created after this timestamp
            
        Returns:
            List of transactions created after the timestamp
        """
        return (
            self.db.query(Transaction)
            .filter(
                and_(
                    Transaction.account_id == account_id,
                    Transaction.user_id == user_id,
                    Transaction.created_at > since_timestamp,
                )
            )
            .order_by(Transaction.created_at.asc())
            .all()
        )
