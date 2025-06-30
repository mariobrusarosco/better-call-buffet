from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session
from app.domains.transactions.schemas import TransactionIn, TransactionResponse
from app.domains.transactions.service import TransactionService

router = APIRouter()


@router.post("/", response_model=TransactionResponse)
def create_transaction_endpoint(
    transaction: TransactionIn,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    service = TransactionService(db)
    return service.create_transaction(transaction, user_id)
