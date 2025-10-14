from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session
from app.domains.balance_points.schemas import (
    BalancePoint,
    BalancePointIn,
    BalancePointUpdateIn,
    BalancePointUpsertIn,
    MonthlyBalanceSummary,
)
from app.domains.balance_points.service import BalancePointService

router = APIRouter()