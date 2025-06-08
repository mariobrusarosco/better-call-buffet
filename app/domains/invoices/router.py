from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.connection_and_session import get_db_session
from .models import Invoice
from .schemas import InvoiceCreate, Invoice as InvoiceSchema

router = APIRouter()

@router.post("/", response_model=InvoiceSchema, status_code=201)
def create_invoice(
    invoice_in: InvoiceCreate,
    db: Session = Depends(get_db_session)
):
    """Store invoice raw content."""
    db_invoice = Invoice(**invoice_in.model_dump())
    db.add(db_invoice)
    db.commit()
    db.refresh(db_invoice)
    return db_invoice 