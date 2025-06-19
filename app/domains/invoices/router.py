from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session
from app.domains.invoices.models import Invoice
from app.domains.invoices.schemas import Invoice as InvoiceSchema
from app.domains.invoices.schemas import InvoiceIn, InvoiceListResponse, InvoiceUpdateIn
from app.domains.invoices.service import InvoiceService

router = APIRouter()


@router.post("/", response_model=InvoiceSchema, status_code=201)
def create_invoice(
    invoice_in: InvoiceIn,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Create a new invoice with business logic validation"""
    service = InvoiceService(db)
    try:
        return service.create_invoice(invoice_in=invoice_in, user_id=current_user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/invoices", response_model=InvoiceSchema, status_code=201)
def create_credit_card_invoice(
    invoice_in: InvoiceIn,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Create a new credit card invoice"""
    service = InvoiceService(db)
    try:
        return service.create_invoice(invoice_in=invoice_in, user_id=current_user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[InvoiceSchema])
def get_invoices(
    include_deleted: bool = Query(False, description="Include soft-deleted invoices"),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get all invoices for the current user"""
    service = InvoiceService(db)
    return service.get_user_invoices(current_user_id, include_deleted)


@router.get("/deleted", response_model=List[InvoiceSchema])
def get_deleted_invoices(
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get all soft-deleted invoices for the current user"""
    service = InvoiceService(db)
    return service.get_deleted_invoices(current_user_id)


@router.get("/count")
def get_invoice_count(
    include_deleted: bool = Query(
        False, description="Include soft-deleted invoices in count"
    ),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get count of invoices for the current user"""
    service = InvoiceService(db)
    count = service.get_invoice_count(current_user_id, include_deleted)
    return {"count": count}


@router.get("/search", response_model=List[InvoiceSchema])
def search_invoices(
    q: str = Query(..., min_length=3, description="Search term for invoice content"),
    include_deleted: bool = Query(False, description="Include soft-deleted invoices"),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Search invoices by content in raw_content JSON field"""
    service = InvoiceService(db)
    try:
        return service.search_invoices(current_user_id, q, include_deleted)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/by-broker/{broker_id}", response_model=List[InvoiceSchema])
def get_invoices_by_broker(
    broker_id: UUID,
    include_deleted: bool = Query(False, description="Include soft-deleted invoices"),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get all invoices for a specific broker"""
    service = InvoiceService(db)
    try:
        return service.get_invoices_by_broker(
            broker_id, current_user_id, include_deleted
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/by-credit-card/{credit_card_id}", response_model=List[InvoiceSchema])
def get_invoices_by_credit_card(
    credit_card_id: UUID,
    include_deleted: bool = Query(False, description="Include soft-deleted invoices"),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get all invoices for a specific credit card"""
    service = InvoiceService(db)
    return service.get_invoices_by_credit_card(
        credit_card_id, current_user_id, include_deleted
    )


@router.get(
    "/credit-card/{credit_card_id}/invoices", response_model=InvoiceListResponse
)
def list_credit_card_invoices(
    credit_card_id: UUID = Path(..., description="The ID of the credit card"),
    page: int = Query(1, description="Page number", ge=1),
    per_page: int = Query(10, description="Items per page", ge=1, le=100),
    include_deleted: bool = Query(False, description="Include soft-deleted invoices"),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get all invoices for a specific credit card with pagination"""
    service = InvoiceService(db)
    invoices = service.get_invoices_by_credit_card(
        credit_card_id, current_user_id, include_deleted, page, per_page
    )

    # Get total count for pagination metadata
    total_count = service.get_invoice_count_by_credit_card(
        credit_card_id, current_user_id, include_deleted
    )

    # Calculate pagination metadata
    total_pages = (total_count + per_page - 1) // per_page
    has_next = page < total_pages
    has_previous = page > 1

    return {
        "data": invoices,
        "meta": {
            "has_next": has_next,
            "has_previous": has_previous,
            "page": page,
            "per_page": per_page,
            "total": total_count,
        },
    }


@router.get("/by-json-field")
def get_invoices_by_json_field(
    json_path: str = Query(
        ..., description="JSON path (e.g., 'amount' or 'transaction.type')"
    ),
    value: str = Query(..., description="Value to match"),
    include_deleted: bool = Query(False, description="Include soft-deleted invoices"),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get invoices where a specific JSON field matches a value"""
    service = InvoiceService(db)
    return service.get_invoices_by_json_field(
        current_user_id, json_path, value, include_deleted
    )


@router.get("/date-range", response_model=List[InvoiceSchema])
def get_invoices_by_date_range(
    start_date: datetime = Query(..., description="Start date (ISO format)"),
    end_date: datetime = Query(..., description="End date (ISO format)"),
    include_deleted: bool = Query(False, description="Include soft-deleted invoices"),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get invoices within a date range"""
    service = InvoiceService(db)
    try:
        return service.get_invoices_by_date_range(
            current_user_id, start_date, end_date, include_deleted
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/broker/{broker_id}/count")
def get_invoice_count_by_broker(
    broker_id: UUID,
    include_deleted: bool = Query(
        False, description="Include soft-deleted invoices in count"
    ),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get count of invoices for a specific broker"""
    service = InvoiceService(db)
    try:
        count = service.get_invoice_count_by_broker(
            broker_id, current_user_id, include_deleted
        )
        return {"broker_id": broker_id, "count": count}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{invoice_id}", response_model=InvoiceSchema)
def get_invoice_by_id(
    invoice_id: UUID,
    include_deleted: bool = Query(False, description="Include soft-deleted invoices"),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get a specific invoice by ID"""
    service = InvoiceService(db)
    invoice = service.get_invoice_by_id(invoice_id, current_user_id, include_deleted)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.get("/{invoice_id}/extract/{json_path}")
def extract_json_field(
    invoice_id: UUID,
    json_path: str,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Extract a specific field from an invoice's raw_content JSON"""
    service = InvoiceService(db)
    value = service.extract_json_field(invoice_id, current_user_id, json_path)
    if value is None:
        raise HTTPException(
            status_code=404, detail="Invoice not found or JSON path not found"
        )
    return {"json_path": json_path, "value": value}


@router.put("/{invoice_id}", response_model=InvoiceSchema)
def update_invoice(
    invoice_id: UUID,
    update_data: InvoiceUpdateIn,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Update an invoice"""
    service = InvoiceService(db)
    try:
        # Convert Pydantic model to dict, excluding None values
        update_dict = update_data.model_dump(exclude_none=True)
        invoice = service.update_invoice(invoice_id, current_user_id, update_dict)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return invoice
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{invoice_id}")
def delete_invoice(
    invoice_id: UUID,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Soft delete an invoice"""
    service = InvoiceService(db)
    invoice = service.delete_invoice(invoice_id, current_user_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {"message": "Invoice deleted successfully"}


@router.post("/{invoice_id}/restore", response_model=InvoiceSchema)
def restore_invoice(
    invoice_id: UUID,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Restore a soft-deleted invoice"""
    service = InvoiceService(db)
    invoice = service.restore_invoice(invoice_id, current_user_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found or not deleted")
    return invoice


@router.delete("/{invoice_id}/permanent")
def permanently_delete_invoice(
    invoice_id: UUID,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Permanently delete an invoice (hard delete) - WARNING: This cannot be undone"""
    service = InvoiceService(db)
    if not service.permanently_delete_invoice(invoice_id, current_user_id):
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {"message": "Invoice permanently deleted"}
