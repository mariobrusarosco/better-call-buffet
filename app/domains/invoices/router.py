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


