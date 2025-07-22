from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.error_handlers import NotFoundError, ValidationError
from app.core.logging_config import get_logger
from app.domains.accounts.service import AccountService
from app.domains.statements.models import Statement
from app.domains.statements.repository import StatementRepository
from app.domains.statements.schemas import (
    StatementFilters,
    StatementIn,
    StatementListMeta,
    StatementListResponse,
    StatementResponse,
)

# Configure logger for this service
logger = get_logger(__name__)


class StatementService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = StatementRepository(db)
        self.account_service = AccountService(db)

    def create_statement(self, statement_in: StatementIn, user_id: UUID) -> Statement:
        """
        Create a new account statement.
        
        Validates account ownership and processes the raw statement data.
        """
        try:
            # Validate account exists and belongs to user
            account = self.account_service.get_account_by_id(
                statement_in.account_id, user_id
            )
            if not account:
                raise NotFoundError(
                    message=f"Account {statement_in.account_id} not found or not accessible",
                    error_code="ACCOUNT_NOT_FOUND"
                )

            # Prepare statement data
            statement_data = {
                "account_id": statement_in.account_id,
                "user_id": user_id,
                "raw_statement": statement_in.raw_statement.model_dump(),
            }

            # Extract and parse structured data from raw statement
            self._enrich_statement_data(statement_data, statement_in.raw_statement)

            # Create statement
            statement = self.repository.create(statement_data)

            logger.info(
                f"Statement created successfully",
                extra={
                    "statement_id": str(statement.id),
                    "account_id": str(statement_in.account_id),
                    "user_id": str(user_id),
                    "transaction_count": len(statement_in.raw_statement.transactions),
                }
            )

            return statement

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error creating statement: {str(e)}")
            raise ValidationError(
                message="Failed to create statement",
                error_code="STATEMENT_CREATION_FAILED"
            )

    def get_account_statements_with_filters(
        self,
        account_id: UUID,
        user_id: UUID,
        filters: Optional[StatementFilters] = None,
    ) -> StatementListResponse:
        """Get paginated statements for a specific account"""
        
        # Validate account exists and belongs to user
        account = self.account_service.get_account_by_id(account_id, user_id)
        if not account:
            raise NotFoundError(
                message=f"Account {account_id} not found or not accessible",
                error_code="ACCOUNT_NOT_FOUND"
            )

        # Set default filters if none provided
        if filters is None:
            filters = StatementFilters()

        # Validate pagination parameters
        filters.page = max(1, filters.page)
        filters.per_page = min(100, max(1, filters.per_page))

        try:
            statements, total_count = self.repository.get_account_statements_with_filters(
                account_id=account_id,
                user_id=user_id,
                filters=filters,
            )

            # Calculate pagination metadata
            total_pages = (total_count + filters.per_page - 1) // filters.per_page
            has_next = filters.page < total_pages
            has_previous = filters.page > 1

            # Convert to response schemas
            statement_responses = [
                StatementResponse.model_validate(statement) for statement in statements
            ]

            # Create metadata
            meta = StatementListMeta(
                total=total_count,
                page=filters.page,
                per_page=filters.per_page,
                has_next=has_next,
                has_previous=has_previous,
            )

            logger.info(
                f"Retrieved {len(statements)} statements for account {account_id}",
                extra={
                    "account_id": str(account_id),
                    "user_id": str(user_id),
                    "total_count": total_count,
                    "page": filters.page,
                }
            )

            return StatementListResponse(data=statement_responses, meta=meta)

        except Exception as e:
            logger.error(f"Error retrieving statements for account {account_id}: {str(e)}")
            raise

    def get_statement_by_id(self, statement_id: UUID, user_id: UUID) -> Statement:
        """Get statement by ID"""
        statement = self.repository.get_by_id(statement_id, user_id)
        if not statement:
            raise NotFoundError(
                message=f"Statement {statement_id} not found",
                error_code="STATEMENT_NOT_FOUND"
            )
        return statement

    def _enrich_statement_data(self, statement_data: dict, raw_statement) -> None:
        """
        Extract structured data from raw statement and add to statement_data.
        
        This method parses dates, amounts, and other structured information
        from the raw statement format.
        """
        try:
            # Parse period dates if available
            if hasattr(raw_statement, 'period') and raw_statement.period:
                period_parts = raw_statement.period.split(' - ')
                if len(period_parts) == 2:
                    try:
                        # Parse dates in format "06/02/2025 - 07/04/2025"
                        period_start = datetime.strptime(period_parts[0].strip(), "%d/%m/%Y")
                        period_end = datetime.strptime(period_parts[1].strip(), "%d/%m/%Y")
                        statement_data["period_start"] = period_start
                        statement_data["period_end"] = period_end
                    except ValueError:
                        logger.warning("Could not parse period dates from statement")

            # Parse due date
            if hasattr(raw_statement, 'due_date') and raw_statement.due_date:
                try:
                    due_date = datetime.strptime(raw_statement.due_date, "%d/%m/%Y")
                    statement_data["due_date"] = due_date
                except ValueError:
                    logger.warning("Could not parse due date from statement")

            # Extract financial summary (keep as strings to preserve formatting)
            statement_data["total_due"] = getattr(raw_statement, 'total_due', None)
            statement_data["min_payment"] = getattr(raw_statement, 'min_payment', None)
            
            # Extract opening/closing balance from next_due_info or transactions
            if hasattr(raw_statement, 'next_due_info') and raw_statement.next_due_info:
                statement_data["closing_balance"] = raw_statement.next_due_info.balance

        except Exception as e:
            logger.warning(f"Error enriching statement data: {str(e)}")
            # Continue without enrichment rather than failing