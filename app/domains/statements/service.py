import asyncio
import json
import os
from datetime import datetime
from typing import Dict, Optional
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
from app.core.ai import AIClient

# Configure logger for this service
logger = get_logger(__name__)


class StatementService:
    def __init__(self, db: Session, ai_client: Optional[AIClient] = None):
        self.db = db
        self.repository = StatementRepository(db)
        self.account_service = AccountService(db)
        self.ai_client = ai_client

    def create_statement(self, statement_in: StatementIn, user_id: UUID) -> Statement:
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

            # Extract bank statement balances (keep as strings to preserve formatting)
            statement_data["opening_balance"] = getattr(raw_statement, 'opening_balance', None)
            statement_data["closing_balance"] = getattr(raw_statement, 'closing_balance', None)
            
            logger.info(
                f"Enriched bank statement data",
                extra={
                    "period_start": statement_data.get("period_start"),
                    "period_end": statement_data.get("period_end"),
                    "opening_balance": statement_data.get("opening_balance"),
                    "closing_balance": statement_data.get("closing_balance")
                }
            )

        except Exception as e:
            logger.warning(f"Error enriching statement data: {str(e)}")
            # Continue without enrichment rather than failing

    def delete_statement(self, statement_id: UUID, user_id: UUID) -> bool:
        """
        Delete a statement by ID with user ownership validation.
        
        Benefits:
        - ✅ User ownership validation
        - ✅ Safe soft deletion with rollback
        - ✅ Logging for audit trail
        
        Args:
            statement_id: UUID of the statement to delete
            user_id: UUID of the user (for ownership validation)
            
        Returns:
            bool: True if deleted, False if not found or not owned
        """
        try:
            # Use repository to delete (handles ownership validation)
            success = self.repository.delete(statement_id, user_id)
            
            if success:
                logger.info(
                    f"Statement deleted successfully",
                    extra={
                        "statement_id": str(statement_id),
                        "user_id": str(user_id),
                    }
                )
            else:
                logger.warning(
                    f"Statement not found or not owned by user",
                    extra={
                        "statement_id": str(statement_id),
                        "user_id": str(user_id),
                    }
                )
                
            return success
            
        except Exception as e:
            logger.error(f"Error deleting statement {statement_id}: {str(e)}")
            raise

    async def parse_pdf_and_create_statement(
        self,
        pdf_content: bytes,
        filename: str,
        account_id: UUID,
        user_id: UUID,
    ) -> Statement:
        """
        🎯 Parse PDF statement and create database record - NO TIMEOUT LIMITS!
        
        This replaces the Netlify function that was timing out. The process:
        1. Extract text from PDF using PyPDF2 or similar
        2. Send extracted text to OpenAI for structured parsing
        3. Create statement record with parsed data
        
        Benefits over Netlify function:
        - ✅ No 10-second timeout limit
        - ✅ More memory and CPU available
        - ✅ Direct database access
        - ✅ Better error handling and logging
        """
        try:
            logger.info(
                f"Starting PDF parsing for file: {filename}",
                extra={
                    "filename": filename,
                    "file_size": len(pdf_content),
                    "account_id": str(account_id),
                    "user_id": str(user_id),
                }
            )

            # Step 1: Extract text from PDF
            pdf_text = await self._extract_pdf_text(pdf_content)
            
            if not pdf_text.strip():
                raise ValidationError(
                    message="Could not extract text from PDF. File may be corrupted or image-based.",
                    error_code="PDF_TEXT_EXTRACTION_FAILED"
                )
            # Step 2: Parse with OpenAI GPT
            parsed_data = await self._parse_with_ai_client(pdf_text, filename)
            
            logger.info(
                f"AI parsing completed",
                extra={
                    "filename": filename,
                    "transactions_count": len(parsed_data.get("transactions", [])),
                }
            )

            # Step 3: Create statement record
            from app.domains.statements.schemas import StatementIn
            
            statement_in = StatementIn(
                account_id=account_id,
                raw_statement=parsed_data
            )
            
            # Use existing create_statement method
            statement = self.create_statement(statement_in, user_id)

            return statement

        except ValidationError:
            raise
        except Exception as e:
            logger.error(
                f"PDF parsing failed: {str(e)}",
                extra={
                    "filename": filename,
                    "account_id": str(account_id),
                    "user_id": str(user_id),
                    "error": str(e),
                }
            )
            raise ValidationError(
                message=f"PDF parsing failed: {str(e)}",
                error_code="PDF_PARSING_FAILED"
            )

    async def _extract_pdf_text(self, pdf_content: bytes) -> str:
        """Extract text from PDF using multiple methods"""
        def extract_text():
            text_parts = []
            
            # Method 1: Try pdfplumber first (better for complex PDFs)
            try:
                import pdfplumber
                import io
                
                logger.info("Trying pdfplumber extraction...")
                pdf_stream = io.BytesIO(pdf_content)
                
                with pdfplumber.open(pdf_stream) as pdf:
                    logger.info(f"PDF has {len(pdf.pages)} pages")
                    
                    for i, page in enumerate(pdf.pages):
                        try:
                            page_text = page.extract_text()
                            if page_text and page_text.strip():
                                text_parts.append(page_text)
                                logger.info(f"Page {i+1}: extracted {len(page_text)} characters")
                            else:
                                logger.warning(f"Page {i+1}: no text extracted")
                        except Exception as e:
                            logger.error(f"Error on page {i+1}: {str(e)}")
                
                if text_parts:
                    logger.info(f"pdfplumber extracted {len(text_parts)} pages successfully")
                    return "\n".join(text_parts)
                    
            except Exception as e:
                logger.warning(f"pdfplumber failed: {str(e)}")
            
            # Method 2: Try PyPDF2 fallback
            try:
                import PyPDF2
                import io
                
                logger.info("Trying PyPDF2 extraction...")
                pdf_stream = io.BytesIO(pdf_content)
                pdf_reader = PyPDF2.PdfReader(pdf_stream)
                
                for i, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text and page_text.strip():
                            text_parts.append(page_text)
                            logger.info(f"PyPDF2 page {i+1}: extracted {len(page_text)} characters")
                    except Exception as e:
                        logger.error(f"PyPDF2 error on page {i+1}: {str(e)}")
                
                if text_parts:
                    logger.info(f"PyPDF2 extracted {len(text_parts)} pages successfully")
                    return "\n".join(text_parts)
                    
            except Exception as e:
                logger.warning(f"PyPDF2 failed: {str(e)}")
            
            # If both methods fail
            raise ValidationError(
                message="Could not extract text from PDF. The file might be image-based, password-protected, or corrupted.",
                error_code="PDF_TEXT_EXTRACTION_FAILED"
            )
        
        # Run in thread to avoid blocking the async event loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, extract_text)

    async def _parse_with_ai_client(self, pdf_text: str, filename: str) -> Dict:
        """
        Parse extracted PDF text using AI client for BANK STATEMENTS.
        
        Returns a dict compatible with RawBankStatement schema.
        """
        if not self.ai_client:
            raise ValidationError(
                message="AI client not configured", 
                error_code="AI_CLIENT_NOT_CONFIGURED"
            )
        
        try:
            # Use AI client specialized method for BANK STATEMENTS ONLY
            response = await self.ai_client.parse_bank_statement(
                text=pdf_text,
                language="pt"
            )
            
            if not response.success:
                error_msg = response.error or "Unknown AI processing error"
                logger.error(f"AI parsing failed: {error_msg}")
                raise ValidationError(
                    message=f"AI processing failed: {error_msg}",
                    error_code="AI_PROCESSING_FAILED"
                )
            
            if not response.data:
                raise ValidationError(
                    message="AI returned empty response",
                    error_code="AI_EMPTY_RESPONSE"
                )
            
            # Use FinancialData directly - no conversion needed since both use TransactionData
            financial_data = response.data
            
            # Build RawBankStatement compatible dict (NO credit card fields!)
            parsed_data = {
                "period": financial_data.period,
                "opening_balance": getattr(financial_data, 'opening_balance', "") or "",
                "closing_balance": getattr(financial_data, 'closing_balance', "") or "",
                "transactions": financial_data.transactions  # Direct usage - no conversion needed!
            }
            
            return parsed_data
            
        except Exception as e:
            logger.error(f"AI parsing failed: {str(e)}")
            raise ValidationError(
                message=f"AI processing failed: {str(e)}",
                error_code="AI_PROCESSING_FAILED"
            )