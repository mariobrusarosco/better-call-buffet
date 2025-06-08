from uuid import UUID
from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session
from app.domains.brokers.schemas import BrokerIn, BrokerCreate, Broker
from app.domains.brokers.service import BrokersService
from fastapi import APIRouter
from sqlalchemy.orm import Session
from fastapi import Depends


router = APIRouter()

@router.get("/")
async def get_brokers():
    return {"message": "Hello, World!"}


@router.post("/", response_model=Broker)
async def create_broker(broker_in: BrokerIn, db: Session = Depends(get_db_session), current_user_id: UUID = Depends(get_current_user_id)):
    service = BrokersService(db)
    
    # Create the internal schema with user_id
    broker_create = BrokerCreate(
        **broker_in.model_dump(),
        user_id=current_user_id,
    )

    return service.create_broker(broker_in=broker_create)