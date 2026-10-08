from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, cast
from uuid import UUID

from sqlalchemy import and_, asc, desc, func, or_
from sqlalchemy.orm import Session, joinedload

from app.domains.credit_cards.models import CreditCard
from app.domains.tags.models import Tag
from app.domains.transactions.constants import MovementType
from app.domains.transactions.models import Transaction
from app.domains.transactions.schemas import TransactionFilters


class TransactionRepository:
    def __init__(self, db: Session):
        self.db = db

    def _transaction_load_options(self):
        return (
            joinedload(Transaction.account),
            joinedload(Transaction.tags).joinedload(Tag.dimension),
            joinedload(Transaction.credit_card).joinedload(CreditCard.account),
            joinedload(Transaction.vendor),
            joinedload(Transaction.subscription),
        )

    def get_by_id(self, transaction_id: UUID, user_id: UUID) -> Optional[Transaction]:
        """Get a transaction by ID with response relationships."""
        return (
            self.db.query(Transaction)
            .options(*self._transaction_load_options())
            .filter(
                and_(Transaction.id == transaction_id, Transaction.user_id == user_id)
            )
            .first()
        )

    def get_by_ids_for_update(
        self, transaction_ids: List[UUID], user_id: UUID
    ) -> List[Transaction]:
        """Load owned transactions and lock them until commit or rollback."""
        return (
            self.db.query(Transaction)
            .filter(
                and_(
                    Transaction.id.in_(transaction_ids),
                    Transaction.user_id == user_id,
                    Transaction.is_deleted.is_(False),
                )
            )
            .with_for_update()
            .all()
        )

    def get_by_ids(
        self, transaction_ids: List[UUID], user_id: UUID
    ) -> List[Transaction]:
        """Reload owned transactions with response relationships."""
        transactions = (
            self.db.query(Transaction)
            .options(*self._transaction_load_options())
            .populate_existing()
            .filter(
                and_(
                    Transaction.id.in_(transaction_ids),
                    Transaction.user_id == user_id,
                    Transaction.is_deleted.is_(False),
                )
            )
            .all()
        )
        transactions_by_id: Dict[UUID, Transaction] = {
            cast(UUID, transaction.id): transaction for transaction in transactions
        }
        return [
            transactions_by_id[transaction_id]
            for transaction_id in transaction_ids
            if transaction_id in transactions_by_id
        ]

    def create(self, transaction_data: dict):
        try:
            transaction = Transaction(**transaction_data)
            self.db.add(transaction)
            self.db.commit()
            self.db.refresh(transaction)

            # Reload with tag, account, card, vendor, and subscription relationships.
            transaction = (
                self.db.query(Transaction)
                .options(*self._transaction_load_options())
                .filter(Transaction.id == transaction.id)
                .first()
            )
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
            transactions = [Transaction(**data) for data in transactions_data]
            self.db.add_all(transactions)
            self.db.commit()
            return [cast(UUID, transaction.id) for transaction in transactions]
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
        # Base query with response relationships.
        query = (
            self.db.query(Transaction)
            .options(*self._transaction_load_options())
            .filter(
                and_(
                    Transaction.account_id == account_id, Transaction.user_id == user_id
                )
            )
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
        # Include direct account transactions and transactions on linked cards.
        query = (
            self.db.query(Transaction)
            .options(*self._transaction_load_options())
            .filter(
                and_(
                    Transaction.user_id
                    == user_id,  # Always ensure user owns transactions
                    or_(
                        # Direct account transactions
                        Transaction.account_id == account_id,
                        # Credit card transactions where the card belongs to this account
                        Transaction.credit_card_id.in_(
                            self.db.query(CreditCard.id)
                            .filter(
                                and_(
                                    CreditCard.account_id == account_id,
                                    CreditCard.user_id == user_id,
                                    CreditCard.is_active == True,
                                    CreditCard.is_deleted == False,
                                )
                            )
                            .subquery()
                        ),
                    ),
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
        # Base query with response relationships.
        query = (
            self.db.query(Transaction)
            .options(*self._transaction_load_options())
            .filter(
                and_(
                    Transaction.credit_card_id == credit_card_id,
                    Transaction.user_id == user_id,
                    Transaction.is_deleted == False,
                )
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
            query = query.filter(Transaction.movement_type.in_(filters.movement_type))
        if filters.tag_ids:
            predicates = [
                Transaction.tags.any(Tag.id == tag_id) for tag_id in filters.tag_ids
            ]
            if filters.tag_match == "any":
                query = query.filter(or_(*predicates))
            else:
                for predicate in predicates:
                    query = query.filter(predicate)
        if filters.exclude_tag_ids:
            for tag_id in filters.exclude_tag_ids:
                query = query.filter(~Transaction.tags.any(Tag.id == tag_id))
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

        # Vendor & Subscription filters
        if filters.vendor_id:
            query = query.filter(Transaction.vendor_id == filters.vendor_id)
        if filters.subscription_id:
            query = query.filter(Transaction.subscription_id == filters.subscription_id)

        return query

    def _apply_sorting(self, query, filters: TransactionFilters):
        sort_fields = {
            "date": Transaction.date,
            "amount": Transaction.amount,
            "created_at": Transaction.created_at,
        }

        default_field = Transaction.date
        field = sort_fields.get(filters.sort_by or default_field, default_field)

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
        - ✅ Eager loads tag and display relationships
        """
        # Base query for all user transactions with response relationships.
        query = (
            self.db.query(Transaction)
            .options(*self._transaction_load_options())
            .filter(Transaction.user_id == user_id)
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

    def get_transactions_for_timeline(
        self, account_id: UUID, user_id: UUID, start_date: date, end_date: date
    ) -> List[Transaction]:
        return (
            self.db.query(Transaction)
            .options(*self._transaction_load_options())
            .filter(
                and_(
                    Transaction.account_id == account_id,
                    Transaction.user_id == user_id,
                    Transaction.date >= start_date,
                    Transaction.date <= end_date,
                    Transaction.is_deleted == False,
                    Transaction.ignored
                    == False,  # Exclude ignored transactions from balance
                )
            )
            .order_by(Transaction.date.asc())
            .all()
        )

    def get_balance_before_date(
        self, account_id: UUID, user_id: UUID, start_date: date
    ) -> Decimal:
        """
        Calculate balance before a given date.

        IMPORTANT: Respects movement_type:
        - income: adds to balance
        - expense: subtracts from balance

        NOTE: This method shares the same CASE logic as get_account_total_balance().
        The duplication is intentional — each serves a distinct use case:
        - get_balance_before_date: Starting point for balance timeline charts
          (see BalancePointService.calculate_balance_timeline)
        - get_account_total_balance: Current total balance for account listings
          (see BalancePointService.calculate_account_balance_from_transactions)
        """
        from sqlalchemy import case

        # Sum with conditional: add income/investment, subtract expense/transfer
        total = (
            self.db.query(
                func.sum(
                    case(
                        (
                            Transaction.movement_type == MovementType.INCOME,
                            Transaction.amount,
                        ),
                        (
                            Transaction.movement_type == MovementType.INVESTMENT,
                            Transaction.amount,
                        ),
                        else_=-Transaction.amount,
                    )
                )
            )
            .filter(
                and_(
                    Transaction.account_id == account_id,
                    Transaction.user_id == user_id,
                    Transaction.date
                    < start_date,  # Changed from <= to < (before the start date)
                    Transaction.is_deleted == False,
                    Transaction.ignored
                    == False,  # Exclude ignored transactions from balance
                )
            )
            .scalar()
        )

        return total or Decimal("0.00")

    def get_account_total_balance(self, account_id: UUID, user_id: UUID) -> Decimal:
        """
        Calculate total balance for an account by summing ALL transactions.

        Same movement_type logic as get_balance_before_date, but without a date cutoff:
        - income/investment: adds to balance
        - expense/transfer/other: subtracts from balance

        NOTE: This method shares the same CASE logic as get_balance_before_date().
        The duplication is intentional — each serves a distinct use case:
        - get_account_total_balance: Current total balance for account listings
          (see BalancePointService.calculate_account_balance_from_transactions)
        - get_balance_before_date: Starting point for balance timeline charts
          (see BalancePointService.calculate_balance_timeline)
        """
        from sqlalchemy import case

        total = (
            self.db.query(
                func.sum(
                    case(
                        (
                            Transaction.movement_type == MovementType.INCOME,
                            Transaction.amount,
                        ),
                        (
                            Transaction.movement_type == MovementType.INVESTMENT,
                            Transaction.amount,
                        ),
                        else_=-Transaction.amount,
                    )
                )
            )
            .filter(
                and_(
                    Transaction.account_id == account_id,
                    Transaction.user_id == user_id,
                    Transaction.is_deleted == False,
                    Transaction.ignored == False,
                )
            )
            .scalar()
        )

        return total or Decimal("0.00")

    def get_transaction_count(self, account_id: UUID, user_id: UUID) -> int:
        return (
            self.db.query(Transaction)
            .filter(
                and_(
                    Transaction.account_id == account_id,
                    Transaction.user_id == user_id,
                    Transaction.is_deleted == False,
                )
            )
            .count()
        )

    def bulk_delete_by_ids(self, transaction_ids: List[UUID], user_id: UUID) -> int:
        """
        Bulk delete transactions by IDs, ensuring user ownership.

        Benefits:
        - ✅ User ownership validation for all transactions
        - ✅ High performance bulk delete via SQLAlchemy
        - ✅ Consistent error handling with rollback
        - ✅ Returns count of deleted transactions

        Args:
            transaction_ids: List of UUIDs to delete
            user_id: UUID of the user (for ownership validation)

        Returns:
            int: Number of transactions actually deleted

        Raises:
            Exception: If bulk delete fails, rolls back transaction
        """
        try:
            # Delete transactions with user ownership validation
            deleted_count = (
                self.db.query(Transaction)
                .filter(
                    and_(
                        Transaction.id.in_(transaction_ids),
                        Transaction.user_id == user_id,
                    )
                )
                .delete(synchronize_session=False)
            )

            self.db.commit()
            return deleted_count

        except Exception as e:
            self.db.rollback()
            raise e

    def delete_by_id(self, transaction_id: UUID, user_id: UUID) -> bool:
        """
        Delete a single transaction by ID, ensuring user ownership.

        Benefits:
        - ✅ User ownership validation
        - ✅ Safe deletion with rollback
        - ✅ CASCADE delete handles related records
        - ✅ Returns success status

        Args:
            transaction_id: UUID of the transaction to delete
            user_id: UUID of the user (for ownership validation)

        Returns:
            bool: True if deleted, False if not found or not owned

        Raises:
            Exception: If deletion fails, rolls back transaction
        """
        try:
            # Find transaction and verify ownership
            transaction = (
                self.db.query(Transaction)
                .filter(
                    and_(
                        Transaction.id == transaction_id, Transaction.user_id == user_id
                    )
                )
                .first()
            )

            if not transaction:
                return False

            # Delete the transaction (CASCADE will handle related records)
            self.db.delete(transaction)
            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            raise e

    def update_transaction(
        self, transaction_id: UUID, user_id: UUID, update_data: Dict[str, Any]
    ) -> Optional[Transaction]:
        try:
            transaction = (
                self.db.query(Transaction)
                .options(*self._transaction_load_options())
                .filter(
                    and_(
                        Transaction.id == transaction_id, Transaction.user_id == user_id
                    )
                )
                .first()
            )

            if not transaction:
                return None

            # `exclude_unset=True` in the service already limits updates to fields the
            # client actually sent. Preserve explicit `null` values here so PATCH can
            # clear nullable relationships like `vendor_id` or `subscription_id`.
            for key, value in update_data.items():
                setattr(transaction, key, value)

            transaction.updated_at = datetime.utcnow()

            self.db.commit()
            self.db.refresh(transaction)

            return transaction

        except Exception as e:
            self.db.rollback()
            raise e

    def bulk_update_transactions(
        self,
        transactions: List[Transaction],
        user_id: UUID,
        update_data: Dict[str, Any],
    ) -> List[Transaction]:
        """Apply updates inside the caller's still-open database transaction."""
        transaction_ids = [cast(UUID, transaction.id) for transaction in transactions]
        updated_at = datetime.utcnow()

        for transaction in transactions:
            for key, value in update_data.items():
                setattr(transaction, key, value)
            setattr(transaction, "updated_at", updated_at)

        self.db.flush()
        return self.get_by_ids(transaction_ids, user_id)
