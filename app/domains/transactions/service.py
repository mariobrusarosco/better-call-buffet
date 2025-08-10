import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.error_handlers import NotFoundError, ValidationError
from app.core.logging_config import get_logger
from app.domains.accounts.service import AccountService
from app.domains.credit_cards.schemas import CreditCardFilters
from app.domains.credit_cards.service import CreditCardService
from app.domains.transactions.models import Transaction
from app.domains.transactions.repository import TransactionRepository
from app.domains.transactions.schemas import (
    TransactionBulkRequest,
    TransactionBulkResponse,
    TransactionFilters,
    TransactionIn,
    TransactionListMeta,
    TransactionListResponse,
    TransactionResponse,
    TransactionResult,
)

# Configure logger for this service
logger = get_logger(__name__)


class TransactionService:
    def __init__(self, db: Session):
        self.db = db  # Store db session for bulk operations
        self.repository = TransactionRepository(db)
        self.account_service = AccountService(db)
        self.credit_card_service = CreditCardService(db)

    def create_transactions_bulk(
        self, transactions_data: List[Dict[str, Any]]
    ) -> List[UUID]:
        try:
            self.db.bulk_insert_mappings(Transaction, transactions_data)
            self.db.commit()
            transaction_ids = [tx_data["id"] for tx_data in transactions_data]
            return transaction_ids

        except Exception as e:
            self.db.rollback()
            raise e

    def create_transactions_from_data(
        self, transaction_data_list: List[Dict[str, Any]], user_id: UUID
    ) -> List[UUID]:
        if not transaction_data_list:
            return []

        return self.create_transactions_bulk(transaction_data_list)

    def create_transactions_bulk_with_validation(
        self, bulk_request: TransactionBulkRequest, user_id: UUID
    ) -> TransactionBulkResponse:
        """
        Create multiple transactions with individual validation and detailed error reporting.
        
        Returns success/failure status for each transaction individually.
        """
        # Validate XOR constraints upfront
        try:
            bulk_request.validate_all_constraints()
        except ValueError as e:
            logger.error(f"Bulk transaction validation failed: {str(e)}")
            raise ValidationError(
                message=str(e),
                error_code="BULK_VALIDATION_FAILED"
            )

        results = []
        successful_transactions = []
        
        for i, transaction_data in enumerate(bulk_request.transactions):
            try:
                # Validate account/credit card ownership
                self._validate_transaction_ownership(transaction_data, user_id)
                
                # Prepare transaction data for database
                tx_dict = transaction_data.model_dump()
                tx_dict["user_id"] = user_id
                tx_dict["id"] = uuid.uuid4()  # Generate ID for bulk insert
                
                successful_transactions.append(tx_dict)
                
                results.append(TransactionResult(
                    success=True,
                    transaction_id=tx_dict["id"],
                    original_data=transaction_data
                ))
                
                logger.debug(f"Transaction {i} validated successfully")
                
            except Exception as e:
                error_message = str(e)
                error_code = getattr(e, 'error_code', 'VALIDATION_ERROR')
                
                results.append(TransactionResult(
                    success=False,
                    error_message=error_message,
                    error_code=error_code,
                    original_data=transaction_data
                ))
                
                logger.warning(
                    f"Transaction {i} validation failed",
                    extra={
                        "user_id": str(user_id),
                        "error": error_message,
                        "error_code": error_code,
                        "transaction_index": i
                    }
                )

        # Bulk insert successful transactions using repository
        if successful_transactions:
            try:
                created_ids = self.repository.bulk_create(successful_transactions)
                
                logger.info(
                    f"Bulk transaction insert completed",
                    extra={
                        "user_id": str(user_id),
                        "total_submitted": len(bulk_request.transactions),
                        "successful": len(successful_transactions),
                        "failed": len(bulk_request.transactions) - len(successful_transactions),
                        "created_transaction_ids": [str(id) for id in created_ids]
                    }
                )
                
            except Exception as e:
                logger.error(f"Bulk insert failed: {str(e)}")
                
                # Mark all successful validations as failed due to database error
                for result in results:
                    if result.success:
                        result.success = False
                        result.transaction_id = None
                        result.error_message = "Database insert failed"
                        result.error_code = "DATABASE_ERROR"
                
                successful_transactions = []

        # Calculate summary statistics
        total_successful = len(successful_transactions)
        total_failed = len(bulk_request.transactions) - total_successful
        
        return TransactionBulkResponse(
            total_submitted=len(bulk_request.transactions),
            total_successful=total_successful,
            total_failed=total_failed,
            results=results
        )

    def _validate_transaction_ownership(self, transaction_data, user_id: UUID) -> None:
        """Validate that user owns the account or credit card specified in transaction"""
        if transaction_data.account_id:
            try:
                self.account_service.get_account_by_id(transaction_data.account_id, user_id)
            except NotFoundError:
                raise ValidationError(
                    message=f"Account {transaction_data.account_id} not found or not accessible",
                    error_code="ACCOUNT_NOT_FOUND"
                )
        
        if transaction_data.credit_card_id:
            try:
                filters = CreditCardFilters(credit_card_id=transaction_data.credit_card_id)
                self.credit_card_service.get_user_unique_credit_card_with_filters(user_id, filters)
            except NotFoundError:
                raise ValidationError(
                    message=f"Credit card {transaction_data.credit_card_id} not found or not accessible",
                    error_code="CREDIT_CARD_NOT_FOUND"
                )

    def create_transaction(
        self, transaction: TransactionIn, user_id: UUID
    ) -> Transaction:
        transaction_data = transaction.model_dump()
        transaction_data["user_id"] = user_id

        return self.repository.create(transaction_data)

    def check_transaction_validity(
        self,
        transaction_account_id: UUID,
        transaction_credit_card_id: UUID,
        user_id: UUID,
    ) -> None:
        try:
            account = None
            credit_card = None

            if transaction_account_id:
                account_id = transaction_account_id
                account = self.account_service.get_account_by_id(account_id, user_id)

            if transaction_credit_card_id:
                credit_card_id = transaction_credit_card_id
                filters = CreditCardFilters(credit_card_id=credit_card_id)
                credit_card = (
                    self.credit_card_service.get_user_unique_credit_card_with_filters(
                        user_id, filters
                    )
                )

            if not account and not credit_card:
                logger.warning(
                    "Transaction creation failed - account nor credit card not found",
                    extra={
                        "user_id": str(user_id),
                        "account_id": str(account_id),
                        "credit_card_id": str(credit_card_id),
                        "error_code": "ACCOUNT_AND_CREDIT_CARD_NOT_FOUND",
                    },
                )
                raise NotFoundError(
                    message=f"Account with ID '{account_id}' not found",
                    error_code="TRANSACTION_ACCOUNT_NOT_FOUND",
                )
        except Exception as e:
            raise e

    def get_account_transactions_with_filters(
        self,
        account_id: UUID,
        user_id: UUID,
        filters: Optional[TransactionFilters] = None,
        include_credit_cards: bool = False,
    ) -> TransactionListResponse:
        """
        Get account transactions using structured filters.

        Benefits:
        - ✅ Consistent API across all transaction endpoints
        - ✅ Type-safe filter validation
        - ✅ Easy to add new filtering capabilities
        - ✅ Self-documenting through schema
        """
        # Set default filters if none provided
        if filters is None:
            filters = TransactionFilters()

        # Validate pagination parameters
        filters.page = max(1, filters.page)
        filters.per_page = min(100, max(1, filters.per_page))

        try:
            if include_credit_cards:
                transactions, total_count = (
                    self.repository.get_account_and_related_credit_card_transactions_with_filters(
                        account_id=account_id,
                        user_id=user_id,
                        filters=filters,
                    )
                )
            else:
                transactions, total_count = (
                    self.repository.get_account_transactions_with_filters(
                        account_id=account_id,
                        user_id=user_id,
                        filters=filters,
                    )
                )

            # Calculate pagination metadata
            total_pages = (total_count + filters.per_page - 1) // filters.per_page
            has_next = filters.page < total_pages
            has_previous = filters.page > 1

            # Convert to response schemas
            transaction_responses = [
                TransactionResponse.from_orm(transaction)
                for transaction in transactions
            ]

            # Create metadata
            meta = TransactionListMeta(
                total=total_count,
                page=filters.page,
                per_page=filters.per_page,
                has_next=has_next,
                has_previous=has_previous,
            )
            return TransactionListResponse(data=transaction_responses, meta=meta)

        except Exception as e:
            logger.error(
                f"Error retrieving transactions for account {account_id}: {str(e)}"
            )
            raise

    def get_credit_card_transactions_with_filters(
        self,
        credit_card_id: UUID,
        user_id: UUID,
        filters: Optional[TransactionFilters] = None,
    ) -> TransactionListResponse:
        """
        Get credit card transactions using structured filters.

        Same benefits as account transactions method.
        """
        # Set default filters if none provided
        if filters is None:
            filters = TransactionFilters()

        # Validate pagination parameters
        filters.page = max(1, filters.page)
        filters.per_page = min(100, max(1, filters.per_page))

        try:
            transactions, total_count = (
                self.repository.get_credit_card_transactions_with_filters(
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
            transaction_responses = [
                TransactionResponse.from_orm(transaction)
                for transaction in transactions
            ]

            # Create metadata
            meta = TransactionListMeta(
                total=total_count,
                page=filters.page,
                per_page=filters.per_page,
                has_next=has_next,
                has_previous=has_previous,
            )

            logger.info(
                f"Retrieved {len(transactions)} transactions for credit card {credit_card_id}, "
                f"page {filters.page}/{total_pages}"
            )

            return TransactionListResponse(data=transaction_responses, meta=meta)

        except Exception as e:
            logger.error(
                f"Error retrieving transactions for credit card {credit_card_id}: {str(e)}"
            )
            raise
