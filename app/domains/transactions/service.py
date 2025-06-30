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
    """
    Service layer for Transaction business logic.
    Uses TransactionRepository for data access operations.
    """

    def __init__(self, db: Session):
        self.repository = TransactionRepository(db)
        self.account_service = AccountService(db)
        self.credit_card_service = CreditCardService(db)

    def create_transaction(
        self, transaction: TransactionIn, user_id: UUID
    ) -> Transaction:
        try:
            logger.info(
                "Creating transaction",
                extra={
                    "user_id": str(user_id),
                    "account_id": (
                        str(transaction.account_id) if transaction.account_id else None
                    ),
                    "amount": transaction.amount,
                    "operation": "create_transaction",
                },
            )
            account = None
            credit_card = None
            transaction_data = transaction.model_dump()
            transaction_data["user_id"] = user_id

            if transaction.account_id:
                account_id = transaction.account_id
                account = self.account_service.get_account_by_id(account_id, user_id)

            if transaction.credit_card_id:
                credit_card_id = transaction.credit_card_id
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

            # Create transaction through repository
            created_transaction = self.repository.create(transaction_data)
            # Log successful creation
            logger.info(
                "Transaction created successfully",
                extra={
                    "user_id": str(user_id),
                    "transaction_id": str(created_transaction.id),
                    "account_id": str(account.id) if account else None,
                    "credit_card_id": str(credit_card.id) if credit_card else None,
                    "amount": created_transaction.amount,
                    "operation": "create_transaction",
                },
            )

            return created_transaction
        except Exception as e:
            logger.error(
                "Transaction creation failed",
                extra={
                    "user_id": str(user_id),
                    "error": str(e),
                },
            )
            raise e
