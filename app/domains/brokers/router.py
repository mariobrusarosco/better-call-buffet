from uuid import UUID
from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session
from app.domains.brokers.schemas import BrokerIn, Broker
from app.domains.brokers.service import BrokersService
from fastapi import APIRouter
from sqlalchemy.orm import Session
from fastapi import Depends


router = APIRouter()

@router.get("/")
async def get_brokers(db: Session = Depends(get_db_session), user_id: UUID = Depends(get_current_user_id)):
    service = BrokersService(db)
    return service.get_all_user_brokers(user_id=user_id)


@router.post("/", response_model=Broker)
async def create_broker(broker_in: BrokerIn, db: Session = Depends(get_db_session), current_user_id: UUID = Depends(get_current_user_id)):
    service = BrokersService(db)
    return service.create_broker(broker_in=broker_in, user_id=current_user_id)