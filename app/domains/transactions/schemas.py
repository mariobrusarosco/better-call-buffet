from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class TransactionBase(BaseModel):
    account_id: Optional[UUID] = None
    credit_card_id: Optional[UUID] = None
    broker_id: UUID
    is_paid: bool
    date: datetime
    amount: float
    description: str
    movement_type: str
    category: str


class TransactionIn(TransactionBase):
    pass


class TransactionResponse(TransactionBase):
    pass
