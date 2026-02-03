"""
Pydantic schemas for Data Transfer domain

Defines request/response models for export and import operations.
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class ExportFormat(str, Enum):
    """Supported export formats"""
    CSV = "csv"
    # Future: JSON = "json", EXCEL = "excel"


class ImportStrategy(str, Enum):
    """Import strategies for handling existing data"""
    APPEND = "append"  # Only add new records (default)
    # Future: REPLACE = "replace", MERGE = "merge"


class ExportStatus(str, Enum):
    """Export job status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ImportStatus(str, Enum):
    """Import job status"""
    PENDING = "pending"
    VALIDATING = "validating"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Export Schemas

class ExportRequest(BaseModel):
    """Request model for initiating data export"""
    date_from: Optional[date] = Field(
        None,
        description="Start date for transaction filter (inclusive)"
    )
    date_to: Optional[date] = Field(
        None,
        description="End date for transaction filter (inclusive)"
    )
    include_deleted: bool = Field(
        False,
        description="Include soft-deleted records in export"
    )
    format: ExportFormat = Field(
        ExportFormat.CSV,
        description="Export file format"
    )

    @field_validator("date_to")
    @classmethod
    def validate_date_range(cls, v, values):
        """Ensure date_to is after date_from if both provided"""
        if v and values.data.get("date_from") and v < values.data.get("date_from"):
            raise ValueError("date_to must be after or equal to date_from")
        return v


class ExportResponse(BaseModel):
    """Response model for export operation"""
    export_id: str = Field(
        description="Unique identifier for this export job"
    )
    status: ExportStatus = Field(
        description="Current status of the export job"
    )
    file_size: Optional[int] = Field(
        None,
        description="Size of the generated file in bytes"
    )
    row_count: Optional[int] = Field(
        None,
        description="Number of rows exported"
    )
    download_url: Optional[str] = Field(
        None,
        description="URL to download the exported file"
    )
    created_at: datetime = Field(
        description="When the export was initiated"
    )
    completed_at: Optional[datetime] = Field(
        None,
        description="When the export completed"
    )
    error_message: Optional[str] = Field(
        None,
        description="Error message if export failed"
    )

    class Config:
        from_attributes = True


class ExportProgress(BaseModel):
    """Progress update for long-running export"""
    export_id: str
    status: ExportStatus
    progress_percentage: int = Field(ge=0, le=100)
    current_step: str
    entities_processed: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of entities processed by type"
    )


# Import Schemas

class ImportValidationRequest(BaseModel):
    """Request model for CSV validation (without importing)"""
    dry_run: bool = Field(
        True,
        description="If true, only validate without importing"
    )


class ImportRequest(BaseModel):
    """Request model for initiating data import"""
    strategy: ImportStrategy = Field(
        ImportStrategy.APPEND,
        description="How to handle existing data"
    )
    validate_only: bool = Field(
        False,
        description="Only validate the file without importing"
    )
    skip_errors: bool = Field(
        True,
        description="Continue importing valid rows even if some rows have errors"
    )


class ImportValidationResult(BaseModel):
    """Result of CSV validation"""
    valid: bool = Field(
        description="Whether the CSV is valid for import"
    )
    row_count: int = Field(
        description="Total number of data rows (excluding header)"
    )
    estimated_entities: Dict[str, int] = Field(
        default_factory=dict,
        description="Estimated count of entities to be created by type"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Non-critical issues found during validation"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Critical errors that would prevent import"
    )


class ImportStatistics(BaseModel):
    """Statistics about an import operation"""
    total_rows: int = Field(
        description="Total rows in the CSV file"
    )
    processed_rows: int = Field(
        description="Rows successfully processed"
    )
    skipped_rows: int = Field(
        description="Rows skipped (duplicates or errors)"
    )
    error_rows: int = Field(
        description="Rows with errors"
    )


class EntityCreationStats(BaseModel):
    """Statistics about entities created during import"""
    brokers: int = Field(default=0)
    accounts: int = Field(default=0)
    credit_cards: int = Field(default=0)
    categories: int = Field(default=0)
    vendors: int = Field(default=0)
    subscriptions: int = Field(default=0)
    installment_plans: int = Field(default=0)
    installments: int = Field(default=0)
    transactions: int = Field(default=0)


class ImportResponse(BaseModel):
    """Response model for import operation"""
    import_id: str = Field(
        description="Unique identifier for this import job"
    )
    status: ImportStatus = Field(
        description="Current status of the import job"
    )
    statistics: Optional[ImportStatistics] = Field(
        None,
        description="Import statistics"
    )
    entities_created: Optional[EntityCreationStats] = Field(
        None,
        description="Count of entities created by type"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="List of errors encountered"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="List of warnings"
    )
    created_at: datetime = Field(
        description="When the import was initiated"
    )
    completed_at: Optional[datetime] = Field(
        None,
        description="When the import completed"
    )

    class Config:
        from_attributes = True


class ImportProgress(BaseModel):
    """Progress update for long-running import"""
    import_id: str
    status: ImportStatus
    progress_percentage: int = Field(ge=0, le=100)
    current_step: str
    rows_processed: int
    entities_created: EntityCreationStats


# Error Response Schemas

class FieldError(BaseModel):
    """Detailed field-level error"""
    row: int = Field(description="Row number in CSV (1-indexed)")
    column: str = Field(description="Column name")
    value: Any = Field(description="The invalid value")
    error: str = Field(description="Error description")


class ImportErrorResponse(BaseModel):
    """Detailed error response for import failures"""
    error: str = Field(description="General error message")
    field_errors: List[FieldError] = Field(
        default_factory=list,
        description="Field-level errors"
    )
    row_errors: Dict[int, List[str]] = Field(
        default_factory=dict,
        description="Errors grouped by row number"
    )


# File Download Schema

class FileDownloadResponse(BaseModel):
    """Response for file download endpoints"""
    filename: str = Field(description="Name of the file")
    content_type: str = Field(description="MIME type of the file")
    content_length: int = Field(description="Size of file in bytes")
    content_disposition: str = Field(
        description="Content-Disposition header value"
    )


# Health/Status Schemas

class DataTransferHealthResponse(BaseModel):
    """Health check response for data transfer service"""
    status: str = Field(default="healthy")
    active_exports: int = Field(
        default=0,
        description="Number of active export jobs"
    )
    active_imports: int = Field(
        default=0,
        description="Number of active import jobs"
    )
    last_export: Optional[datetime] = Field(
        None,
        description="Timestamp of last export"
    )
    last_import: Optional[datetime] = Field(
        None,
        description="Timestamp of last import"
    )