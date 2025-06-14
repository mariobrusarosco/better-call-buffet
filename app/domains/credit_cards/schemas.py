from datetime import datetime
from pydantic import BaseModel
from uuid import UUID

class CreditCardIn(BaseModel):
    account_id: UUID
    broker_id: UUID
    name: str
    description: str
    due_date: datetime
    balance: float = 0.0
    is_active: bool = True