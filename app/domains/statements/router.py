from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session
from app.domains.statements.schemas import (
    StatementFilters,
    StatementIn,
    StatementListResponse,
    StatementResponse,
)
from app.domains.statements.service import StatementService

router = APIRouter()


@router.post("/", response_model=StatementResponse, status_code=201)
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


@router.get("/", response_model=StatementListResponse)
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