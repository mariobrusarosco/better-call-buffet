from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.error_handlers import NotFoundError, ValidationError
from app.core.logging_config import get_logger
from app.domains.accounts.service import AccountService
from app.domains.credit_cards.schemas import CreditCardFilters
from app.domains.credit_cards.service import CreditCardService
from app.domains.transactions.models import Transaction
from app.domains.transactions.repository import TransactionRepository
from app.domains.transactions.schemas import TransactionIn

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
            logger.error(
                "Transaction creation failed - account nor credit card not found",
                extra={
                    "user_id": str(user_id),
                    "account_id": str(account_id),
                    "credit_card_id": str(credit_card_id),
                    "error_code": "ACCOUNT_AND_CREDIT_CARD_NOT_FOUND",
                },
            )
            raise e
