import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.domains.brokers.service import BrokersService
from app.domains.credit_cards.schemas import CreditCardFilters
from app.domains.credit_cards.service import CreditCardService
from app.domains.invoices.models import Invoice
from app.domains.invoices.repository import InvoiceRepository
from app.domains.invoices.schemas import InvoiceIn


class InvoiceCreditCardNotFoundError(Exception):
    pass


class InvoiceBrokerNotFoundError(Exception):
    pass


class InvoiceRawInvoiceEmptyError(Exception):
    pass


class InvoiceService:
    """
    Service layer for Invoice business logic.
    Uses InvoiceRepository for data access operations.
    """

    def __init__(self, db: Session):
        self.repository = InvoiceRepository(db)
        self.broker_service = BrokersService(db)
        self.credit_card_service = CreditCardService(db)

    def create_invoice(self, invoice_in: InvoiceIn, user_id: UUID) -> Invoice:
        credit_card = self.credit_card_service.get_credit_card_by_id(
            invoice_in.credit_card_id, user_id
        )
        if not credit_card:
            raise InvoiceCreditCardNotFoundError(
                f"Credit card {invoice_in.credit_card_id} not found or does not belong to user"
            )

        # Validate broker ownership
        broker = self.broker_service.get_broker_by_id(credit_card.broker_id, user_id)
        if not broker:
            raise InvoiceBrokerNotFoundError(
                f"Broker {credit_card.broker_id} not found or does not belong to user"
            )

        if not invoice_in.raw_invoice:
            raise InvoiceRawInvoiceEmptyError("Raw invoice data cannot be empty")

        # Prepare invoice data
        invoice_data = invoice_in.model_dump()
        invoice_data["user_id"] = user_id
        invoice_data["broker_id"] = (
            credit_card.broker_id
        )  # Set broker_id from credit card

        # Transform transactions to add missing id fields
        if (
            "raw_invoice" in invoice_data
            and "transactions" in invoice_data["raw_invoice"]
        ):
            transactions = invoice_data["raw_invoice"]["transactions"]
            for i, transaction in enumerate(transactions):
                if "id" not in transaction:
                    transaction["id"] = str(i + 1)  # Simple incremental ID

        return self.repository.create(invoice_data)

    def get_invoice_by_id(
        self, invoice_id: UUID, user_id: UUID, include_deleted: bool = False
    ) -> Optional[Invoice]:
        """Get invoice by ID with user validation"""
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

    # def search_invoices(
    #     self, user_id: UUID, search_term: str, include_deleted: bool = False
    # ) -> List[Invoice]:
    #     """
    #     Search invoices by content in raw_content JSON field.

    #     Args:
    #         user_id: ID of the user
    #         search_term: Term to search for in invoice content
    #         include_deleted: Whether to include soft-deleted invoices

    #     Returns:
    #         List of matching invoices

    #     Raises:
    #         ValueError: If search term is too short
    #     """
    #     if not search_term or len(search_term.strip()) < 3:
    #         raise ValueError("Search term must be at least 3 characters long")

    #     return self.repository.search_in_raw_content(
    #         user_id, search_term.strip(), include_deleted
    #     )

    # def get_invoices_by_json_field(
    #     self, user_id: UUID, json_path: str, value: Any, include_deleted: bool = False
    # ) -> List[Invoice]:
    #     """
    #     Get invoices where a specific JSON field matches a value.

    #     Example: Find all invoices with amount = 100.0
    #     """
    #     return self.repository.get_by_json_field(
    #         user_id, json_path, value, include_deleted
    #     )

    # def get_invoices_by_date_range(
    #     self,
    #     user_id: UUID,
    #     start_date: datetime,
    #     end_date: datetime,
    #     include_deleted: bool = False,
    # ) -> List[Invoice]:
    #     """Get invoices within a date range"""
    #     if start_date > end_date:
    #         raise ValueError("Start date must be before end date")

    #     return self.repository.get_by_date_range(
    #         user_id, start_date, end_date, include_deleted
    #     )

    # def update_invoice(
    #     self, invoice_id: UUID, user_id: UUID, update_data: dict
    # ) -> Optional[Invoice]:
    #     """
    #     Update an invoice with business logic validation.

    #     Args:
    #         invoice_id: ID of the invoice to update
    #         user_id: ID of the user updating the invoice
    #         update_data: Dictionary of fields to update

    #     Returns:
    #         Updated invoice if successful, None if not found

    #     Raises:
    #         ValueError: If validation fails
    #     """
    #     invoice = self.repository.get_by_id_and_user(invoice_id, user_id)
    #     if not invoice:
    #         return None

    #     # Business logic: Validate broker_id if being updated
    #     if "broker_id" in update_data:
    #         broker = self.broker_service.get_broker_by_id(
    #             update_data["broker_id"], user_id
    #         )
    #         if not broker:
    #             raise ValueError("Broker not found or does not belong to user")

    #     # Business logic: Validate credit_card_id if being updated
    #     if "credit_card_id" in update_data:
    #         credit_card = self.credit_card_service.get_credit_card_by_id(
    #             update_data["credit_card_id"], user_id
    #         )
    #         if not credit_card:
    #             raise ValueError("Credit card not found or does not belong to user")

    #     # Business logic: Validate raw_invoice if being updated
    #     if "raw_invoice" in update_data:
    #         if not update_data["raw_invoice"]:
    #             raise ValueError("Raw invoice data cannot be empty")

    #     return self.repository.update(invoice, update_data)

    # def delete_invoice(self, invoice_id: UUID, user_id: UUID) -> Optional[Invoice]:
    #     """Soft delete an invoice"""
    #     invoice = self.repository.get_by_id_and_user(invoice_id, user_id)
    #     if not invoice:
    #         return None

    #     return self.repository.soft_delete(invoice)

    # def restore_invoice(self, invoice_id: UUID, user_id: UUID) -> Optional[Invoice]:
    #     """Restore a soft-deleted invoice"""
    #     invoice = self.repository.get_by_id_and_user(
    #         invoice_id, user_id, include_deleted=True
    #     )
    #     if not invoice or not invoice.is_deleted:
    #         return None

    #     return self.repository.restore(invoice)

    # def permanently_delete_invoice(self, invoice_id: UUID, user_id: UUID) -> bool:
    #     """Permanently delete an invoice (hard delete)"""
    #     invoice = self.repository.get_by_id_and_user(
    #         invoice_id, user_id, include_deleted=True
    #     )
    #     if not invoice:
    #         return False

    #     self.repository.hard_delete(invoice)
    #     return True

    # def get_deleted_invoices(self, user_id: UUID) -> List[Invoice]:
    #     """Get all soft-deleted invoices for a user"""
    #     return self.repository.get_deleted_invoices(user_id)

    # def get_invoice_count(self, user_id: UUID, include_deleted: bool = False) -> int:
    #     """Get count of invoices for a user"""
    #     return self.repository.count_by_user(user_id, include_deleted)

    # def get_invoice_count_by_broker(
    #     self, broker_id: UUID, user_id: UUID, include_deleted: bool = False
    # ) -> int:
    #     """
    #     Get count of invoices for a specific broker.

    #     Args:
    #         broker_id: ID of the broker
    #         user_id: ID of the user
    #         include_deleted: Whether to include soft-deleted invoices

    #     Returns:
    #         Count of invoices for the broker

    #     Raises:
    #         ValueError: If broker doesn't belong to user
    #     """
    #     # Validate broker ownership
    #     broker = self.broker_service.get_broker_by_id(broker_id, user_id)
    #     if not broker:
    #         raise ValueError("Broker not found or does not belong to user")

    #     return self.repository.count_by_broker(broker_id, user_id, include_deleted)

    # def extract_json_field(
    #     self, invoice_id: UUID, user_id: UUID, json_path: str
    # ) -> Any:
    #     """
    #     Extract a specific field from an invoice's raw_invoice JSON.

    #     Args:
    #         invoice_id: ID of the invoice
    #         user_id: ID of the user
    #         json_path: Path to the JSON field (e.g., "transactions.0.amount")

    #     Returns:
    #         The extracted value or None if not found
    #     """
    #     invoice = self.repository.get_by_id_and_user(invoice_id, user_id)
    #     if not invoice:
    #         return None

    #     try:
    #         # Handle nested paths like "transactions.0.amount"
    #         # Convert raw_invoice to dict if it's a Pydantic model
    #         if hasattr(invoice.raw_invoice, "model_dump"):
    #             value = invoice.raw_invoice.model_dump()
    #         else:
    #             value = invoice.raw_invoice

    #         for key in json_path.split("."):
    #             # Handle array indices in the path
    #             if key.isdigit():
    #                 key = int(key)
    #             value = value[key]
    #         return value
    #     except (KeyError, TypeError, IndexError):
    #         return None

    # def _generate_content_hash(self, raw_content: Dict[str, Any]) -> str:
    #     """Generate a hash of the raw content for duplicate detection"""
    #     # Sort the JSON to ensure consistent hashing
    #     content_str = json.dumps(raw_content, sort_keys=True, separators=(",", ":"))
    #     return hashlib.md5(content_str.encode()).hexdigest()

    # def get_invoice_count_by_credit_card(
    #     self, credit_card_id: UUID, user_id: UUID, include_deleted: bool = False
    # ) -> int:
    #     """
    #     Get count of invoices for a specific credit card.

    #     Args:
    #         credit_card_id: ID of the credit card
    #         user_id: ID of the user
    #         include_deleted: Whether to include soft-deleted invoices

    #     Returns:
    #         Count of invoices for the credit card

    #     Raises:
    #         ValueError: If credit card doesn't belong to user
    #     """
    #     # Validate credit card ownership
    #     credit_card = self.credit_card_service.get_credit_card_by_id(
    #         credit_card_id, user_id
    #     )
    #     if not credit_card:
    #         raise ValueError("Credit card not found or does not belong to user")

    #     return self.repository.count_by_credit_card(
    #         credit_card_id, user_id, include_deleted
    #     )
