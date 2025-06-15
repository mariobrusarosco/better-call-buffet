from datetime import datetime
from pydantic import BaseModel
from uuid import UUID
from typing import Optional

class CreditCardIn(BaseModel):
    account_id: UUID
    name: str
    description: Optional[str] = None
    due_date: datetime
    balance: float = 0.0
    is_active: bool = True