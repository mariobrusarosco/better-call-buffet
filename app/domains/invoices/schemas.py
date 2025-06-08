from typing import Dict, Any
from pydantic import BaseModel
from uuid import UUID

class InvoiceCreate(BaseModel):
    credit_card_id: UUID
    broker_id: UUID
    raw_content: Dict[str, Any]

class Invoice(BaseModel):
    id: UUID
    credit_card_id: UUID
    broker_id: UUID
    raw_content: Dict[str, Any]

    class Config:
        from_attributes = True 