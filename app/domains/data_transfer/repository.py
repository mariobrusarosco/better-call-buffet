"""
Repository layer for Data Transfer domain

Handles all database operations for export and import functionality.
Provides methods to fetch data for export and create entities during import.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID, uuid4
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import and_, or_

# Import all required models
from app.domains.users.models import User
from app.domains.brokers.models import Broker
from app.domains.accounts.models import Account
from app.domains.credit_cards.models import CreditCard
from app.domains.transactions.models import Transaction
from app.domains.categories.models import UserCategory
from app.domains.vendors.models import Vendor
from app.domains.subscriptions.models import Subscription
from app.domains.installments.models import InstallmentPlan, Installment
from app.domains.balance_points.models import BalancePoint
from app.domains.invoices.models import Invoice
from app.domains.statements.models import Statement

logger = logging.getLogger(__name__)


class DataTransferRepository:
    """
    Repository for data transfer operations.
    Handles all database queries for export and import functionality.
    """

    def __init__(self, db: Session):
        self.db = db

    # ==================== EXPORT METHODS ====================

    def fetch_user_financial_data(
        self,
        user_id: UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        include_deleted: bool = False
    ) -> Dict[str, List[Any]]:
        """
        Fetch all financial data for a user.

        Args:
            user_id: User UUID
            date_from: Optional start date filter
            date_to: Optional end date filter
            include_deleted: Whether to include soft-deleted records

        Returns:
            Dictionary with entity types as keys and lists of entities as values
        """
        data = {}

        # Fetch brokers
        broker_query = self.db.query(Broker).filter(Broker.user_id == user_id)
        if not include_deleted:
            broker_query = broker_query.filter(Broker.is_active == True)
        data["brokers"] = broker_query.all()

        # Fetch accounts
        account_query = self.db.query(Account).filter(Account.user_id == user_id)
        if not include_deleted:
            account_query = account_query.filter(Account.is_active == True)
        data["accounts"] = account_query.all()

        # Fetch credit cards
        card_query = self.db.query(CreditCard).filter(CreditCard.user_id == user_id)
        if not include_deleted:
            card_query = card_query.filter(CreditCard.is_deleted == False)
        data["credit_cards"] = card_query.all()

        # Fetch categories (with hierarchy)
        category_query = self.db.query(UserCategory).filter(
            UserCategory.user_id == user_id
        )
        if not include_deleted:
            category_query = category_query.filter(UserCategory.is_active == True)
        data["categories"] = category_query.all()

        # Fetch vendors
        data["vendors"] = self.db.query(Vendor).filter(
            Vendor.user_id == user_id
        ).all()

        # Fetch subscriptions
        subscription_query = self.db.query(Subscription).filter(
            Subscription.user_id == user_id
        )
        if not include_deleted:
            subscription_query = subscription_query.filter(Subscription.is_active == True)
        data["subscriptions"] = subscription_query.all()

        # Fetch installment plans
        installment_plan_query = self.db.query(InstallmentPlan).filter(
            InstallmentPlan.user_id == user_id
        )
        if not include_deleted:
            installment_plan_query = installment_plan_query.filter(
                InstallmentPlan.status != "cancelled"
            )
        data["installment_plans"] = installment_plan_query.options(
            selectinload(InstallmentPlan.installments)
        ).all()

        # Fetch transactions with date filtering
        transaction_query = self.db.query(Transaction).filter(
            Transaction.user_id == user_id
        )

        if date_from:
            transaction_query = transaction_query.filter(Transaction.date >= date_from)
        if date_to:
            transaction_query = transaction_query.filter(Transaction.date <= date_to)
        if not include_deleted:
            transaction_query = transaction_query.filter(Transaction.is_deleted == False)

        # Load with relationships for efficient access
        transaction_query = transaction_query.options(
            joinedload(Transaction.account),
            joinedload(Transaction.credit_card),
            joinedload(Transaction.category_rel),
            joinedload(Transaction.vendor),
            joinedload(Transaction.subscription),
            joinedload(Transaction.installment)
        )

        data["transactions"] = transaction_query.all()

        return data

    def get_entity_counts(self, user_id: UUID) -> Dict[str, int]:
        """
        Get counts of all entities for a user.

        Args:
            user_id: User UUID

        Returns:
            Dictionary with entity types and their counts
        """
        return {
            "brokers": self.db.query(Broker).filter(
                Broker.user_id == user_id,
                Broker.is_active == True
            ).count(),
            "accounts": self.db.query(Account).filter(
                Account.user_id == user_id,
                Account.is_active == True
            ).count(),
            "credit_cards": self.db.query(CreditCard).filter(
                CreditCard.user_id == user_id,
                CreditCard.is_deleted == False
            ).count(),
            "categories": self.db.query(UserCategory).filter(
                UserCategory.user_id == user_id,
                UserCategory.is_active == True
            ).count(),
            "vendors": self.db.query(Vendor).filter(
                Vendor.user_id == user_id
            ).count(),
            "subscriptions": self.db.query(Subscription).filter(
                Subscription.user_id == user_id,
                Subscription.is_active == True
            ).count(),
            "transactions": self.db.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.is_deleted == False
            ).count(),
        }

    # ==================== IMPORT METHODS ====================

    def find_or_create_broker(
        self,
        user_id: UUID,
        name: str,
        description: Optional[str] = None
    ) -> Broker:
        """
        Find existing broker or create new one.

        Args:
            user_id: User UUID
            name: Broker name
            description: Optional broker description

        Returns:
            Broker instance (existing or new)
        """
        # Check for existing broker
        existing = self.db.query(Broker).filter(
            Broker.user_id == user_id,
            Broker.name == name
        ).first()

        if existing:
            logger.debug(f"Found existing broker: {name}")
            return existing

        # Create new broker
        broker = Broker(
            id=uuid4(),
            user_id=user_id,
            name=name,
            description=description or "",
            colors=[],  # Default empty colors
            logo="",    # Default empty logo
            is_active=True
        )
        self.db.add(broker)
        logger.info(f"Created new broker: {name}")
        return broker

    def find_or_create_account(
        self,
        user_id: UUID,
        broker_id: UUID,
        name: str,
        account_type: str = "OTHER",
        currency: str = "USD",
        description: Optional[str] = None
    ) -> Account:
        """
        Find existing account or create new one.

        Args:
            user_id: User UUID
            broker_id: Broker UUID
            name: Account name
            account_type: Type of account
            currency: Currency code
            description: Optional description

        Returns:
            Account instance (existing or new)
        """
        # Check for existing account
        existing = self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.broker_id == broker_id,
            Account.name == name
        ).first()

        if existing:
            logger.debug(f"Found existing account: {name}")
            return existing

        # Create new account
        account = Account(
            id=uuid4(),
            user_id=user_id,
            broker_id=broker_id,
            name=name,
            description=description or "",
            type=account_type,
            currency=currency,
            is_active=True
        )
        self.db.add(account)
        logger.info(f"Created new account: {name}")
        return account

    def find_or_create_credit_card(
        self,
        user_id: UUID,
        broker_id: UUID,
        account_id: UUID,
        name: str,
        brand: Optional[str] = None,
        last_four_digits: Optional[str] = None,
        credit_limit: Optional[Decimal] = None,
        due_date: Optional[int] = None
    ) -> CreditCard:
        """
        Find existing credit card or create new one.

        Args:
            user_id: User UUID
            broker_id: Broker UUID
            account_id: Account UUID
            name: Card name
            brand: Card brand (Visa, Mastercard, etc.)
            last_four_digits: Last 4 digits of card
            credit_limit: Credit limit
            due_date: Monthly due date (1-31)

        Returns:
            CreditCard instance (existing or new)
        """
        # Check for existing credit card
        existing = self.db.query(CreditCard).filter(
            CreditCard.user_id == user_id,
            CreditCard.account_id == account_id,
            CreditCard.name == name
        ).first()

        if existing:
            logger.debug(f"Found existing credit card: {name}")
            return existing

        # Create new credit card
        card = CreditCard(
            id=uuid4(),
            user_id=user_id,
            broker_id=broker_id,
            account_id=account_id,
            name=name,
            brand=brand or "",
            last_four_digits=last_four_digits or "",
            due_date=due_date,
            credit_limit=credit_limit or Decimal("0"),
            current_balance=Decimal("0"),
            available_credit=credit_limit or Decimal("0"),
            is_active=True,
            is_deleted=False
        )
        self.db.add(card)
        logger.info(f"Created new credit card: {name}")
        return card

    def find_or_create_category(
        self,
        user_id: UUID,
        name: str,
        parent_id: Optional[UUID] = None
    ) -> UserCategory:
        """
        Find existing category or create new one.

        Args:
            user_id: User UUID
            name: Category name
            parent_id: Optional parent category ID

        Returns:
            UserCategory instance (existing or new)
        """
        # Check for existing category
        existing = self.db.query(UserCategory).filter(
            UserCategory.user_id == user_id,
            UserCategory.name == name,
            UserCategory.parent_id == parent_id
        ).first()

        if existing:
            logger.debug(f"Found existing category: {name}")
            return existing

        # Create new category
        category = UserCategory(
            id=uuid4(),
            user_id=user_id,
            name=name,
            parent_id=parent_id,
            display_order=0,  # Default order
            is_active=True
        )
        self.db.add(category)
        logger.info(f"Created new category: {name}")
        return category

    def find_or_create_vendor(
        self,
        user_id: UUID,
        name: str,
        website: Optional[str] = None
    ) -> Vendor:
        """
        Find existing vendor or create new one.

        Args:
            user_id: User UUID
            name: Vendor name
            website: Optional website URL

        Returns:
            Vendor instance (existing or new)
        """
        # Check for existing vendor
        existing = self.db.query(Vendor).filter(
            Vendor.user_id == user_id,
            Vendor.name == name
        ).first()

        if existing:
            logger.debug(f"Found existing vendor: {name}")
            return existing

        # Create new vendor
        vendor = Vendor(
            id=uuid4(),
            user_id=user_id,
            name=name,
            logo_url="",
            website=website or ""
        )
        self.db.add(vendor)
        logger.info(f"Created new vendor: {name}")
        return vendor

    def find_or_create_subscription(
        self,
        user_id: UUID,
        name: str,
        vendor_id: Optional[UUID] = None,
        category_id: Optional[UUID] = None,
        amount: Optional[Decimal] = None,
        billing_cycle: Optional[str] = None,
        next_due_date: Optional[date] = None
    ) -> Subscription:
        """
        Find existing subscription or create new one.

        Args:
            user_id: User UUID
            name: Subscription name
            vendor_id: Optional vendor ID
            category_id: Optional category ID
            amount: Subscription amount
            billing_cycle: Billing cycle (monthly, yearly, etc.)
            next_due_date: Next due date

        Returns:
            Subscription instance (existing or new)
        """
        # Check for existing subscription
        existing = self.db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.name == name,
            Subscription.vendor_id == vendor_id
        ).first()

        if existing:
            logger.debug(f"Found existing subscription: {name}")
            return existing

        # Create new subscription
        subscription = Subscription(
            id=uuid4(),
            user_id=user_id,
            vendor_id=vendor_id,
            category_id=category_id,
            name=name,
            amount=amount or Decimal("0"),
            billing_cycle=billing_cycle or "monthly",
            next_due_date=next_due_date,
            is_active=True
        )
        self.db.add(subscription)
        logger.info(f"Created new subscription: {name}")
        return subscription

    def find_or_create_installment_plan(
        self,
        user_id: UUID,
        name: str,
        total_amount: Decimal,
        installment_count: int,
        vendor_id: Optional[UUID] = None,
        category_id: Optional[UUID] = None,
        credit_card_id: Optional[UUID] = None,
        start_date: Optional[date] = None
    ) -> InstallmentPlan:
        """
        Find existing installment plan or create new one.

        Args:
            user_id: User UUID
            name: Plan name
            total_amount: Total amount
            installment_count: Number of installments
            vendor_id: Optional vendor ID
            category_id: Optional category ID
            credit_card_id: Optional credit card ID
            start_date: Plan start date

        Returns:
            InstallmentPlan instance (existing or new)
        """
        # Check for existing plan
        existing = self.db.query(InstallmentPlan).filter(
            InstallmentPlan.user_id == user_id,
            InstallmentPlan.name == name,
            InstallmentPlan.total_amount == total_amount
        ).first()

        if existing:
            logger.debug(f"Found existing installment plan: {name}")
            return existing

        # Create new installment plan
        plan = InstallmentPlan(
            id=uuid4(),
            user_id=user_id,
            vendor_id=vendor_id,
            category_id=category_id,
            credit_card_id=credit_card_id,
            name=name,
            description="",
            total_amount=total_amount,
            installment_count=installment_count,
            start_date=start_date or date.today(),
            status="active"
        )
        self.db.add(plan)
        logger.info(f"Created new installment plan: {name}")
        return plan

    def create_transaction(
        self,
        user_id: UUID,
        broker_id: UUID,
        date: date,
        amount: Decimal,
        description: str,
        movement_type: str,
        account_id: Optional[UUID] = None,
        credit_card_id: Optional[UUID] = None,
        from_account_id: Optional[UUID] = None,
        to_account_id: Optional[UUID] = None,
        category_id: Optional[UUID] = None,
        vendor_id: Optional[UUID] = None,
        subscription_id: Optional[UUID] = None,
        installment_id: Optional[UUID] = None,
        is_paid: bool = True,
        ignored: bool = False
    ) -> Transaction:
        """
        Create a new transaction.

        Args:
            user_id: User UUID
            broker_id: Broker UUID
            date: Transaction date
            amount: Transaction amount
            description: Transaction description
            movement_type: Type of movement (INCOME, EXPENSE, TRANSFER)
            account_id: Optional account ID
            credit_card_id: Optional credit card ID
            from_account_id: Optional source account ID (for transfers)
            to_account_id: Optional destination account ID (for transfers)
            category_id: Optional category ID
            vendor_id: Optional vendor ID
            subscription_id: Optional subscription ID
            installment_id: Optional installment ID
            is_paid: Payment status
            ignored: Whether transaction is ignored

        Returns:
            Transaction instance
        """
        # Check for duplicate transaction
        existing_query = self.db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.date == date,
            Transaction.amount == amount,
            Transaction.description == description,
            Transaction.is_deleted == False
        )

        # Add optional field checks for better duplicate detection
        if account_id:
            existing_query = existing_query.filter(Transaction.account_id == account_id)
        if credit_card_id:
            existing_query = existing_query.filter(
                Transaction.credit_card_id == credit_card_id
            )

        if existing_query.first():
            logger.warning(
                f"Duplicate transaction skipped: {date} {amount} {description}"
            )
            return None

        # Create new transaction
        transaction = Transaction(
            id=uuid4(),
            user_id=user_id,
            broker_id=broker_id,
            account_id=account_id,
            credit_card_id=credit_card_id,
            from_account_id=from_account_id,
            to_account_id=to_account_id,
            date=date,
            amount=amount,
            description=description,
            movement_type=movement_type,
            category="",  # Legacy field
            category_id=category_id,
            vendor_id=vendor_id,
            subscription_id=subscription_id,
            installment_id=installment_id,
            is_paid=is_paid,
            is_deleted=False,
            ignored=ignored,
            balance_impact=True  # Default to true
        )
        self.db.add(transaction)
        logger.debug(f"Created new transaction: {date} {amount} {description}")
        return transaction

    def commit_import(self) -> int:
        """
        Commit all pending database changes.

        Returns:
            Number of objects committed
        """
        try:
            # Get count of new objects before commit
            new_count = len(self.db.new)
            self.db.commit()
            logger.info(f"Successfully committed {new_count} objects to database")
            return new_count
        except Exception as e:
            logger.error(f"Error committing import: {e}")
            self.db.rollback()
            raise

    def rollback_import(self):
        """Rollback all pending database changes."""
        self.db.rollback()
        logger.info("Rolled back import transaction")