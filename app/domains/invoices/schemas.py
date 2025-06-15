from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel


# Base schema with shared properties
class InvoiceBase(BaseModel):
    credit_card_id: UUID
    broker_id: UUID
    raw_content: Dict[str, Any]


# Schema for creating an invoice (what frontend sends)
class InvoiceIn(InvoiceBase):
    pass


# Schema for updating an invoice (partial fields)
class InvoiceUpdateIn(BaseModel):
    credit_card_id: Optional[UUID] = None
    broker_id: Optional[UUID] = None
    raw_content: Optional[Dict[str, Any]] = None


# Schema for API responses (what users see)
class Invoice(InvoiceBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
