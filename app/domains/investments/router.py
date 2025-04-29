from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.base import get_db_session
from app.domains.investments.model import Investment as InvestmentModel
from app.domains.investments.schemas import Investment
from app.core.dependencies import get_current_user_id

router = APIRouter(prefix="/investments", tags=["investments"])

@router.get("/", response_model=List[Investment])
async def get_investments(
    db: Session = Depends(get_db_session),
    current_user_id: int = Depends(get_current_user_id)
):
    response = db.query(InvestmentModel).filter(InvestmentModel.user_id == current_user_id).all()
    return response