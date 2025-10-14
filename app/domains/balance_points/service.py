from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.domains.balance_points.models import BalancePoint
from app.domains.balance_points.repository import BalancePointRepository
from app.domains.balance_points.schemas import BalancePointIn
from app.domains.transactions.repository import TransactionRepository
from app.domains.accounts.repository import AccountRepository


class BalancePointService:
    def __init__(self, db: Session):
        pass