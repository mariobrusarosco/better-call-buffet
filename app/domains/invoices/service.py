import hashlib
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.core.utils import safe_parse_date, safe_parse_float
from app.domains.brokers.service import BrokersService
from app.domains.credit_cards.schemas import CreditCardFilters
from app.domains.credit_cards.service import CreditCardService
from app.domains.invoices.models import Invoice
from app.domains.invoices.repository import InvoiceRepository
from app.domains.invoices.schemas import InvoiceIn
from app.domains.transactions.schemas import TransactionIn
from app.domains.transactions.service import TransactionService

# Configure logger for this service
logger = get_logger(__name__)


class InvoiceCreditCardNotFoundError(Exception):
    pass


class InvoiceBrokerNotFoundError(Exception):
    pass


class InvoiceRawInvoiceEmptyError(Exception):
    pass


class InvoiceTransactionProcessingError(Exception):
    """Raised when transaction processing fails during invoice creation"""

    pass


class InvoiceService:
    def __init__(self, db: Session):
        self.repository = InvoiceRepository(db)
        self.broker_service = BrokersService(db)
        self.credit_card_service = CreditCardService(db)
        self.transaction_service = TransactionService(db)

    def _prepare_transactions_from_raw_invoice(
        self,
        raw_transactions: List[Dict[str, Any]],
        credit_card_id: UUID,
        broker_id: UUID,
        user_id: UUID,
    ) -> List[Dict[str, Any]]:
        if not raw_transactions:
            return []

        transaction_data_list = []

        # Transform raw invoice transactions to transaction format
        for i, raw_tx in enumerate(raw_transactions):
            transaction_id = uuid.uuid4()

            # Invoice-specific transformation using utility functions
            transaction_date = safe_parse_date(raw_tx.get("date"))
            amount = safe_parse_float(raw_tx.get("amount"))
            description = raw_tx.get("description", "").strip()
            description = description if description else "No description provided"

            transaction_data_list.append(
                {
                    "id": transaction_id,
                    "account_id": None,  # Credit card transactions don't have accounts
                    "credit_card_id": credit_card_id,
                    "broker_id": broker_id,
                    "user_id": user_id,
                    "is_paid": False,  # New transactions are unpaid by default
                    "date": transaction_date,
                    "amount": amount,
                    "description": description,
                    "movement_type": "DEBIT",  # Credit card transactions are debits
                    "category": raw_tx.get("category", "GENERAL"),  # Default category
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
            )

        return transaction_data_list

    def _create_invoice_transactions(
        self,
        raw_transactions: List[Dict[str, Any]],
        credit_card_id: UUID,
        broker_id: UUID,
        user_id: UUID,
    ) -> List[UUID]:
        try:
            # Step 1: Prepare transactions (Invoice domain responsibility)
            transaction_data_list = self._prepare_transactions_from_raw_invoice(
                raw_transactions, credit_card_id, broker_id, user_id
            )

            if transaction_data_list:
                return self.transaction_service.create_transactions_from_data(
                    transaction_data_list, user_id
                )

            return []

        except Exception as e:
            raise InvoiceTransactionProcessingError(
                f"Failed to create {len(raw_transactions)} transactions for invoice: {str(e)}"
            )

    def create_invoice(self, invoice_in: InvoiceIn, user_id: UUID) -> Invoice:
        # Validate credit card ownership using the filtering pattern
        filters = CreditCardFilters(credit_card_id=invoice_in.credit_card_id)
        credit_card = self.credit_card_service.get_user_unique_credit_card_with_filters(
            user_id, filters
        )
        if not credit_card:
            raise InvoiceCreditCardNotFoundError(
                f"Credit card {invoice_in.credit_card_id} not found or does not belong to user"
            )

        # Validate broker ownership
        broker_id = UUID(
            str(credit_card.broker_id)
        )  # Explicit type conversion for type checker
        broker = self.broker_service.get_broker_by_id(broker_id, user_id)
        if not broker:
            raise InvoiceBrokerNotFoundError(
                f"Broker {broker_id} not found or does not belong to user"
            )

        if not invoice_in.raw_invoice:
            raise InvoiceRawInvoiceEmptyError("Raw invoice data cannot be empty")

        # Prepare invoice data
        invoice_data = invoice_in.model_dump()
        invoice_data["user_id"] = user_id
        invoice_data["broker_id"] = broker_id  # Set broker_id from credit card

        # 🎓 BULK TRANSACTION PROCESSING
        # Process all transactions from the raw invoice in a single efficient operation
        created_transaction_ids = []
        if invoice_data.get("raw_invoice") and invoice_data["raw_invoice"].get(
            "transactions"
        ):
            raw_transactions = invoice_data["raw_invoice"]["transactions"]
            created_transaction_ids = self._create_invoice_transactions(
                raw_transactions,
                UUID(str(credit_card.id)),  # Explicit UUID conversion for type checker
                broker_id,
                user_id,
            )

            # Store transaction IDs in invoice for reference
            invoice_data["transaction_ids"] = created_transaction_ids

        return self.repository.create(invoice_data)

    def get_invoice_by_id(
        self, invoice_id: UUID, user_id: UUID, include_deleted: bool = False
    ) -> Optional[Invoice]:
        return self.repository.get_by_id_and_user(invoice_id, user_id, include_deleted)

    def get_user_invoices(
        self, user_id: UUID, include_deleted: bool = False
    ) -> List[Invoice]:
        """Get all invoices for a user"""
        return self.repository.get_by_user(user_id, include_deleted)

    def get_invoices_by_broker(
        self, broker_id: UUID, user_id: UUID, include_deleted: bool = False
    ) -> List[Invoice]:
        """
        Get all invoices for a specific broker.

        Args:
            broker_id: ID of the broker
            user_id: ID of the user
            include_deleted: Whether to include soft-deleted invoices

        Returns:
            List of invoices for the broker

        Raises:
            ValueError: If broker doesn't belong to user
        """
        # Validate broker ownership
        broker = self.broker_service.get_broker_by_id(broker_id, user_id)
        if not broker:
            raise ValueError("Broker not found or does not belong to user")

        return self.repository.get_by_broker_and_user(
            broker_id, user_id, include_deleted
        )

    def get_invoices_by_credit_card(
        self,
        credit_card_id: UUID,
        user_id: UUID,
        include_deleted: bool = False,
        page: int = 1,
        per_page: int = 10,
    ) -> List[Invoice]:

        print(f"Getting invoices for credit card {credit_card_id}")

        # Validate credit card ownership
        filters = CreditCardFilters(credit_card_id=credit_card_id)
        credit_card = self.credit_card_service.get_user_unique_credit_card_with_filters(
            user_id, filters
        )

        if not credit_card:
            raise ValueError("Credit card not found or does not belong to user")

        return self.repository.get_by_credit_card_and_user(
            credit_card_id, user_id, include_deleted, page, per_page
        )
