"""
Router for Data Transfer domain

Defines API endpoints for exporting and importing financial data.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session
from app.domains.data_transfer.schemas import (
    ExportRequest,
    ExportResponse,
    ImportRequest,
    ImportResponse,
    ImportValidationResult,
    DataTransferHealthResponse
)
from app.domains.data_transfer.service import DataTransferService

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== HEALTH CHECK ====================

@router.get("/health", response_model=DataTransferHealthResponse)
def health_check():
    """
    Health check endpoint for data transfer service.

    Returns basic service status information.
    """
    return DataTransferHealthResponse(
        status="healthy",
        active_exports=0,
        active_imports=0
    )


# ==================== EXPORT ENDPOINTS ====================

@router.post("/export", response_model=ExportResponse)
def export_financial_data(
    request: ExportRequest,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """
    Export user's financial data to CSV format.

    This endpoint generates a CSV file containing all the user's financial data
    including transactions, accounts, credit cards, categories, vendors, and more.

    **Parameters:**
    - **date_from**: Optional start date for filtering transactions (ISO format: YYYY-MM-DD)
    - **date_to**: Optional end date for filtering transactions (ISO format: YYYY-MM-DD)
    - **include_deleted**: Include soft-deleted records in export (default: false)
    - **format**: Export format (currently only CSV is supported)

    **Returns:**
    - Export job details with download URL

    **Example:**
    ```json
    {
      "date_from": "2024-01-01",
      "date_to": "2024-12-31",
      "include_deleted": false,
      "format": "csv"
    }
    ```
    """
    try:
        logger.info(f"Export requested by user {current_user_id}")
        service = DataTransferService(db)
        result = service.export_user_data(current_user_id, request)

        if result.status == "failed":
            raise HTTPException(
                status_code=500,
                detail=f"Export failed: {result.error_message}"
            )

        return result

    except Exception as e:
        logger.error(f"Export endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/{export_id}/download")
def download_export(
    export_id: str,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """
    Download a previously generated export file.

    Returns the CSV file for download. The file will be automatically
    downloaded with a descriptive filename.

    **Parameters:**
    - **export_id**: The export job ID returned from the /export endpoint

    **Returns:**
    - CSV file download

    **Errors:**
    - 404: Export file not found or expired
    - 403: User does not have permission to access this export
    """
    try:
        service = DataTransferService(db)
        result = service.get_export_file(export_id, current_user_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail="Export file not found or has expired"
            )

        content, filename = result

        return Response(
            content=content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== IMPORT ENDPOINTS ====================

@router.post("/import/validate", response_model=ImportValidationResult)
async def validate_import_file(
    file: UploadFile = File(..., description="CSV file to validate"),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """
    Validate a CSV file for import without actually importing the data.

    This endpoint checks the CSV structure, validates required columns,
    and reports any errors or warnings. Use this before importing to
    ensure your file is formatted correctly.

    **Parameters:**
    - **file**: CSV file to validate (multipart/form-data)

    **Returns:**
    - Validation result with:
      - Whether the file is valid
      - Number of rows found
      - Estimated entities to be created
      - List of errors (if any)
      - List of warnings (if any)

    **Example Response:**
    ```json
    {
      "valid": true,
      "row_count": 1500,
      "estimated_entities": {
        "brokers": 3,
        "accounts": 5,
        "transactions": 1500
      },
      "warnings": [],
      "errors": []
    }
    ```
    """
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(
                status_code=400,
                detail="File must be a CSV file"
            )

        # Check file size (50MB limit)
        max_size = 50 * 1024 * 1024  # 50MB
        content = await file.read()

        if len(content) > max_size:
            raise HTTPException(
                status_code=400,
                detail="File size exceeds maximum limit of 50MB"
            )

        # Decode content
        try:
            csv_content = content.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400,
                detail="File must be UTF-8 encoded"
            )

        # Validate CSV
        service = DataTransferService(db)
        result = service.validate_csv(current_user_id, csv_content)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Validation endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import", response_model=ImportResponse)
async def import_financial_data(
    file: UploadFile = File(..., description="CSV file to import"),
    skip_errors: bool = True,
    validate_only: bool = False,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """
    Import financial data from a CSV file.

    This endpoint processes a CSV file and imports the financial data
    into the user's account. The import follows an append-only strategy,
    meaning existing data will not be modified.

    **Parameters:**
    - **file**: CSV file to import (multipart/form-data)
    - **skip_errors**: Continue importing valid rows even if some rows have errors (default: true)
    - **validate_only**: Only validate the file without importing (default: false)

    **Returns:**
    - Import job details with statistics:
      - Total rows processed
      - Entities created by type
      - Any errors encountered
      - Any warnings

    **Import Behavior:**
    - **Append-only**: Existing records are not modified
    - **Duplicate detection**: Transactions with same date, amount, and description are skipped
    - **Entity creation**: Missing entities (accounts, categories, etc.) are created automatically
    - **Relationship resolution**: Entities are linked by name matching

    **CSV Format:**
    - Required columns: transaction_date, transaction_amount, transaction_description, transaction_movement_type
    - Optional columns: account_name, credit_card_name, category_name, vendor_name, etc.
    - See /docs for complete column list

    **Example Response:**
    ```json
    {
      "import_id": "abc123",
      "status": "completed",
      "statistics": {
        "total_rows": 1500,
        "processed_rows": 1450,
        "skipped_rows": 50,
        "error_rows": 0
      },
      "entities_created": {
        "accounts": 5,
        "transactions": 1200
      }
    }
    ```
    """
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(
                status_code=400,
                detail="File must be a CSV file"
            )

        # Check file size (50MB limit)
        max_size = 50 * 1024 * 1024  # 50MB
        content = await file.read()

        if len(content) > max_size:
            raise HTTPException(
                status_code=400,
                detail="File size exceeds maximum limit of 50MB"
            )

        # Decode content
        try:
            csv_content = content.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400,
                detail="File must be UTF-8 encoded"
            )

        # Create import request
        import_request = ImportRequest(
            skip_errors=skip_errors,
            validate_only=validate_only
        )

        # Import data
        logger.info(f"Import requested by user {current_user_id}")
        service = DataTransferService(db)
        result = service.import_user_data(
            current_user_id,
            csv_content,
            import_request
        )

        if result.status == "failed":
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Import failed",
                    "errors": result.errors
                }
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Import endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))