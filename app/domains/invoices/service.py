import asyncio
import hashlib
import json
import os
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
from app.domains.invoices.schemas import Invoice as InvoiceSchema
from app.domains.invoices.schemas import (
    InvoiceFilters,
    InvoiceIn,
    InvoiceListResponse,
    PaginationMeta,
)
from app.domains.transactions.schemas import TransactionIn
from app.domains.transactions.service import TransactionService
from app.core.ai import AIClient

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
    def __init__(self, db: Session, ai_client: Optional[AIClient] = None):
        self.repository = InvoiceRepository(db)
        self.broker_service = BrokersService(db)
        self.credit_card_service = CreditCardService(db)
        self.transaction_service = TransactionService(db)
        self.ai_client = ai_client

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
                    "movement_type": "expense",  # Credit card transactions are expenses
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
    ) -> None:
        """
        🎓 BULK TRANSACTION CREATION

        This method demonstrates efficient bulk processing:
        - Transforms raw invoice data to transaction format
        - Uses bulk insert for performance
        - Maintains data consistency between invoices and transactions
        """
        logger.info(
            f"Processing {len(raw_transactions)} transactions for invoice creation"
        )

        # Prepare transaction data
        transaction_data_list = self._prepare_transactions_from_raw_invoice(
            raw_transactions, credit_card_id, broker_id, user_id
        )

        if transaction_data_list:
            # Create transactions in bulk
            transaction_ids = self.transaction_service.create_transactions_from_data(
                transaction_data_list, user_id
            )
            logger.info(f"✅ Created {len(transaction_ids)} transactions successfully")

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
        if invoice_data.get("raw_invoice") and invoice_data["raw_invoice"].get(
            "transactions"
        ):
            raw_transactions = invoice_data["raw_invoice"]["transactions"]

            # Create all transactions in bulk
            self._create_invoice_transactions(
                raw_transactions,
                UUID(str(credit_card.id)),  # Explicit UUID conversion for type checker
                broker_id,
                user_id,
            )

        return self.repository.create(invoice_data)

    def get_invoice_by_id(self, invoice_id: UUID, user_id: UUID) -> Optional[Invoice]:
        """Get a specific invoice by ID"""
        return self.repository.get_by_id(invoice_id, user_id)

    def get_user_invoices(self, user_id: UUID) -> List[Invoice]:
        """Get all invoices for a user - LEGACY METHOD"""
        return self.repository.get_all_by_user(user_id)

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

    def get_invoices_with_filters(
        self,
        user_id: UUID,
        filters: Optional[InvoiceFilters] = None,
    ) -> InvoiceListResponse:
        """
        Get user invoices using structured filters.

        Benefits:
        - ✅ Consistent API across all invoice endpoints
        - ✅ Type-safe filter validation
        - ✅ Easy to add new filtering capabilities
        - ✅ Self-documenting through schema
        """
        # Set default filters if none provided
        if filters is None:
            filters = InvoiceFilters()

        # Validate pagination parameters
        filters.page = max(1, filters.page)
        filters.per_page = min(100, max(1, filters.per_page))

        try:
            invoices, total_count = self.repository.get_invoices_with_filters(
                user_id=user_id,
                filters=filters,
            )

            # Calculate pagination metadata
            total_pages = (total_count + filters.per_page - 1) // filters.per_page
            has_next = filters.page < total_pages
            has_previous = filters.page > 1

            # Convert to response schemas
            invoice_responses = [
                InvoiceSchema.model_validate(invoice) for invoice in invoices
            ]

            # Create metadata
            meta = PaginationMeta(
                total=total_count,
                page=filters.page,
                per_page=filters.per_page,
                has_next=has_next,
                has_previous=has_previous,
            )

            logger.info(
                f"Retrieved {len(invoices)} invoices for user {user_id}, "
                f"page {filters.page}/{total_pages}"
            )

            return InvoiceListResponse(data=invoice_responses, meta=meta)

        except Exception as e:
            logger.error(f"Error retrieving invoices for user {user_id}: {str(e)}")
            raise

    def get_credit_card_invoices_with_filters(
        self,
        credit_card_id: UUID,
        user_id: UUID,
        filters: Optional[InvoiceFilters] = None,
    ) -> InvoiceListResponse:
        """
        Get credit card invoices using structured filters.
        """
        # Validate credit card ownership first
        card_filters = CreditCardFilters(credit_card_id=credit_card_id)
        credit_card = self.credit_card_service.get_user_unique_credit_card_with_filters(
            user_id, card_filters
        )
        if not credit_card:
            raise ValueError("Credit card not found or does not belong to user")

        # Set default filters if none provided
        if filters is None:
            filters = InvoiceFilters()

        # Ensure credit_card_id filter is set
        filters.credit_card_id = credit_card_id

        # Validate pagination parameters
        filters.page = max(1, filters.page)
        filters.per_page = min(100, max(1, filters.per_page))

        try:
            invoices, total_count = (
                self.repository.get_credit_card_invoices_with_filters(
                    credit_card_id=credit_card_id,
                    user_id=user_id,
                    filters=filters,
                )
            )

            # Calculate pagination metadata
            total_pages = (total_count + filters.per_page - 1) // filters.per_page
            has_next = filters.page < total_pages
            has_previous = filters.page > 1

            # Convert to response schemas
            invoice_responses = [invoice for invoice in invoices]

            # Create metadata
            meta = PaginationMeta(
                total=total_count,
                page=filters.page,
                per_page=filters.per_page,
                has_next=has_next,
                has_previous=has_previous,
            )

            logger.info(
                f"Retrieved {len(invoices)} invoices for credit card {credit_card_id}, "
                f"page {filters.page}/{total_pages}"
            )

            return InvoiceListResponse(data=invoice_responses, meta=meta)

        except Exception as e:
            logger.error(
                f"Error retrieving invoices for credit card {credit_card_id}: {str(e)}"
            )
            raise

    def get_broker_invoices_with_filters(
        self,
        broker_id: UUID,
        user_id: UUID,
        filters: Optional[InvoiceFilters] = None,
    ) -> InvoiceListResponse:
        """
        Get broker invoices using structured filters.
        """
        # Set default filters if none provided
        if filters is None:
            filters = InvoiceFilters()

        # Ensure broker_id filter is set
        filters.broker_id = broker_id

        # Validate pagination parameters
        filters.page = max(1, filters.page)
        filters.per_page = min(100, max(1, filters.per_page))

        try:
            invoices, total_count = self.repository.get_broker_invoices_with_filters(
                broker_id=broker_id,
                user_id=user_id,
                filters=filters,
            )

            # Calculate pagination metadata
            total_pages = (total_count + filters.per_page - 1) // filters.per_page
            has_next = filters.page < total_pages
            has_previous = filters.page > 1

            # Convert to response schemas
            invoice_responses = [invoice for invoice in invoices]

            # Create metadata
            meta = PaginationMeta(
                total=total_count,
                page=filters.page,
                per_page=filters.per_page,
                has_next=has_next,
                has_previous=has_previous,
            )

            logger.info(
                f"Retrieved {len(invoices)} invoices for broker {broker_id}, "
                f"page {filters.page}/{total_pages}"
            )

            return InvoiceListResponse(data=invoice_responses, meta=meta)

        except Exception as e:
            logger.error(f"Error retrieving invoices for broker {broker_id}: {str(e)}")
            raise

    # 🔄 LEGACY METHODS (for backward compatibility)
    def get_invoices_by_credit_card(
        self,
        credit_card_id: UUID,
        user_id: UUID,
        include_deleted: bool = False,
        page: int = 1,
        per_page: int = 10,
    ) -> List[Invoice]:
        """LEGACY METHOD - Use get_credit_card_invoices_with_filters instead."""
        filters = InvoiceFilters(
            credit_card_id=credit_card_id,
            is_deleted=include_deleted,
            page=page,
            per_page=per_page,
        )
        response = self.get_credit_card_invoices_with_filters(
            credit_card_id, user_id, filters
        )
        return response.data

    async def parse_pdf_and_create_invoice(
        self,
        pdf_content: bytes,
        filename: str,
        credit_card_id: UUID,
        user_id: UUID,
    ) -> Invoice:
        """
        🎯 Parse PDF invoice and create database record - NO TIMEOUT LIMITS!
        
        This replaces the Netlify function that was timing out. The process:
        1. Extract text from PDF using PyPDF2 or similar
        2. Send extracted text to OpenAI for structured parsing
        3. Create invoice record with parsed data and transactions
        
        Benefits over Netlify function:
        - ✅ No 10-second timeout limit
        - ✅ More memory and CPU available
        - ✅ Direct database access
        - ✅ Better error handling and logging
        - ✅ Automatic transaction creation from invoice data
        """
        try:
            logger.info(
                f"Starting PDF parsing for invoice: {filename}",
                extra={
                    "filename": filename,
                    "file_size": len(pdf_content),
                    "credit_card_id": str(credit_card_id),
                    "user_id": str(user_id),
                }
            )

            # Step 1: Extract text from PDF
            pdf_text = await self._extract_pdf_text(pdf_content)
            
            if not pdf_text.strip():
                raise InvoiceRawInvoiceEmptyError(
                    "Could not extract text from PDF. File may be corrupted or image-based."
                )

            logger.info(
                f"PDF text extracted successfully",
                extra={
                    "text_length": len(pdf_text),
                    "filename": filename,
                }
            )

            # Step 2: Parse with AI client
            parsed_data = await self._parse_with_ai_client(pdf_text, filename)
            
            logger.info(
                f"AI parsing completed",
                extra={
                    "filename": filename,
                    "transactions_count": len(parsed_data.get("transactions", [])),
                }
            )

            # Step 3: Create invoice record with parsed data
            invoice_in = InvoiceIn(
                credit_card_id=credit_card_id,
                raw_invoice=parsed_data  # This will be the structured data from OpenAI
            )
            
            # Use existing create_invoice method (which also creates transactions)
            invoice = self.create_invoice(invoice_in, user_id)
            
            logger.info(
                f"PDF parsing and invoice creation completed successfully",
                extra={
                    "invoice_id": str(invoice.id),
                    "filename": filename,
                    "processing_time": "completed",
                }
            )
            
            return invoice

        except (InvoiceRawInvoiceEmptyError, InvoiceCreditCardNotFoundError, InvoiceBrokerNotFoundError):
            raise  # Re-raise known invoice errors
        except Exception as e:
            logger.error(
                f"PDF parsing failed: {str(e)}",
                extra={
                    "filename": filename,
                    "credit_card_id": str(credit_card_id),
                    "user_id": str(user_id),
                    "error": str(e),
                }
            )
            raise InvoiceTransactionProcessingError(f"PDF parsing failed: {str(e)}")

    async def _extract_pdf_text(self, pdf_content: bytes) -> str:
        """Extract text from PDF using PyPDF2 - runs in thread to avoid blocking"""
        def extract_text():
            try:
                import PyPDF2
                import io
                
                pdf_stream = io.BytesIO(pdf_content)
                pdf_reader = PyPDF2.PdfReader(pdf_stream)
                
                text_parts = []
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                
                return "\n".join(text_parts)
                
            except ImportError:
                # Fallback: try pdfplumber if PyPDF2 not available
                try:
                    import pdfplumber
                    import io
                    
                    pdf_stream = io.BytesIO(pdf_content)
                    text_parts = []
                    
                    with pdfplumber.open(pdf_stream) as pdf:
                        for page in pdf.pages:
                            page_text = page.extract_text()
                            if page_text:
                                text_parts.append(page_text)
                    
                    return "\n".join(text_parts)
                    
                except ImportError:
                    raise InvoiceRawInvoiceEmptyError(
                        "PDF parsing libraries not installed. Please install PyPDF2 or pdfplumber."
                    )
            except Exception as e:
                raise InvoiceRawInvoiceEmptyError(f"Failed to extract text from PDF: {str(e)}")
        
        # Run in thread to avoid blocking the async event loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, extract_text)

    async def _parse_with_ai_client(self, pdf_text: str, filename: str) -> Dict:
        """Parse extracted PDF text using AI client (supports OpenAI, Ollama, etc.)"""
        if not self.ai_client:
            raise InvoiceRawInvoiceEmptyError("AI client not configured")
        
        try:
            # Use AI client to parse financial document
            response = await self.ai_client.parse_financial_document(
                text=pdf_text,
                document_type="invoice",
                language="pt"
            )
            
            if not response.success:
                error_msg = response.error or "Unknown AI processing error"
                logger.error(f"AI parsing failed: {error_msg}")
                raise InvoiceTransactionProcessingError(f"AI processing failed: {error_msg}")
            
            if not response.data:
                raise InvoiceRawInvoiceEmptyError("AI returned empty response")
            
            # Convert FinancialData model to dict format for compatibility
            financial_data = response.data
            parsed_data = {
                "total_due": financial_data.total_due,
                "due_date": financial_data.due_date,
                "period": financial_data.period,
                "min_payment": financial_data.min_payment,
                "installment_options": [
                    {"months": opt.months, "total": opt.total}
                    for opt in financial_data.installment_options
                ],
                "transactions": [
                    {
                        "date": tx.date,
                        "description": tx.description,
                        "amount": tx.amount,
                        "category": tx.category
                    }
                    for tx in financial_data.transactions
                ],
                "next_due_info": {
                    "amount": financial_data.next_due_info.amount,
                    "balance": financial_data.next_due_info.balance
                } if financial_data.next_due_info else None
            }
            
            return parsed_data
            
        except Exception as e:
            logger.error(f"AI parsing failed: {str(e)}")
            raise InvoiceTransactionProcessingError(f"AI processing failed: {str(e)}")
