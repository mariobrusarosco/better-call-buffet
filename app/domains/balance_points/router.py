from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.connection_and_session import get_db_session
from app.core.dependencies import get_current_user_id
from app.domains.balance_points.service import BalancePointService
from app.domains.balance_points.schemas import BalancePointIn, BalancePoint


router = APIRouter()
    
@router.post("/", response_model=BalancePoint)
def create_balance_point(
    balance_point_in: BalancePointIn,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id)
):
    service = BalancePointService(db)
    return service.create_balance_point(balance_point_in=balance_point_in, user_id=current_user_id)

