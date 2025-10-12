from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id, get_ai_client
from app.core.logging_config import get_logger
from app.db.connection_and_session import get_db_session
from app.core.ai import AIClient
from app.domains.statements.schemas import (
    StatementFilters,
    StatementIn,
    StatementListResponse,
    StatementResponse,
)
from app.domains.statements.service import StatementService

router = APIRouter()


@router.post("", response_model=StatementResponse, status_code=201)
def create_statement_endpoint(
    statement_in: StatementIn,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Create a new account statement.
    
    Processes raw statement data including transactions, balances, and due dates.
    Validates account ownership before creating the statement.
    """
    try:
        service = StatementService(db)
        statement = service.create_statement(statement_in, user_id)
        return StatementResponse.model_validate(statement)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error creating statement")


@router.get("", response_model=StatementListResponse)
def get_statements_endpoint(
    account_id: Optional[UUID] = Query(None, description="Filter by account ID"),
    is_processed: Optional[bool] = Query(None, description="Filter by processing status"),
    is_deleted: Optional[bool] = Query(False, description="Include deleted statements"),
    date_from: Optional[datetime] = Query(None, description="Filter from this date"),
    date_to: Optional[datetime] = Query(None, description="Filter to this date"),
    sort_by: Optional[str] = Query("created_at", description="Sort field"),
    sort_order: Optional[str] = Query("desc", description="Sort order: desc or asc"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Get paginated statements with filtering options.
    
    Can filter by account, processing status, date range, and more.
    """
    try:
        filters = StatementFilters(
            account_id=account_id,
            is_processed=is_processed,
            is_deleted=is_deleted,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            per_page=per_page,
        )

        service = StatementService(db)
        
        # If account_id is provided, get statements for that account
        if account_id:
            return service.get_account_statements_with_filters(
                account_id=account_id,
                user_id=user_id,
                filters=filters,
            )
        else:
            # This would need to be implemented in service for all user statements
            raise HTTPException(
                status_code=400, 
                detail="account_id is required for statement filtering"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving statements: {str(e)}")


@router.get("/{statement_id}", response_model=StatementResponse)
def get_statement_by_id_endpoint(
    statement_id: UUID,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """Get a specific statement by ID"""
    try:
        service = StatementService(db)
        statement = service.get_statement_by_id(statement_id, user_id)
        return StatementResponse.model_validate(statement)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error retrieving statement")


@router.post("/parse-pdf", response_model=StatementResponse, status_code=201)
async def parse_pdf_statement_endpoint(
    file: UploadFile = File(...),
    account_id: UUID = Form(...),
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
    ai_client: AIClient = Depends(get_ai_client),
):
    """
    🎯 Parse credit card PDF statement - NO TIMEOUT LIMITS!
    
    This endpoint replaces the Netlify function that was timing out after 10 seconds.
    
    Benefits:
    - ✅ No serverless timeout constraints (can run as long as needed)
    - ✅ Direct database access (no API round-trips) 
    - ✅ More CPU/memory available on Railway
    - ✅ Consistent error handling with backend architecture
    - ✅ Better logging and monitoring
    
    Process:
    1. Validate PDF file and account ownership
    2. Extract text from PDF using pdf parsing libraries
    3. Process with AI client for structured data extraction
    4. Create statement record directly in database
    5. Return complete statement response
    """
    try:
        # Validate file type
        if not file.filename or not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="File must be a PDF")
        
        if not file.content_type or file.content_type != 'application/pdf':
            raise HTTPException(status_code=400, detail="Invalid file type")
        
        # Validate account ownership
        from app.domains.accounts.service import AccountService
        account_service = AccountService(db)
        account = account_service.get_account_by_id(account_id, user_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Read PDF file
        pdf_content = await file.read()
        
        # Process PDF and create statement
        service = StatementService(db, ai_client)
        statement = await service.parse_pdf_and_create_statement(
            pdf_content=pdf_content,
            filename=file.filename,
            account_id=account_id,
            user_id=user_id,
        )
        
        return StatementResponse.model_validate(statement)
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(
            f"PDF parsing failed: {str(e)}",
            extra={
                "user_id": str(user_id),
                "account_id": str(account_id),
                "filename": file.filename if file.filename else "unknown",
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=500, 
            detail=f"PDF parsing failed: {str(e)}"
        )


@router.delete("/{statement_id}", status_code=204)
def delete_statement_endpoint(
    statement_id: UUID,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Delete a statement by ID.
    
    Performs soft deletion of the statement record.
    Only the statement owner can delete their statements.
    """
    try:
        service = StatementService(db)
        success = service.delete_statement(statement_id, user_id)
        
        if not success:
            raise HTTPException(
                status_code=404, 
                detail="Statement not found or not accessible"
            )
            
        # Return 204 No Content for successful deletion
        return None
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(
            f"Error deleting statement: {str(e)}",
            extra={
                "statement_id": str(statement_id),
                "user_id": str(user_id),
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=500, 
            detail="Error deleting statement"
        )