from uuid import UUID
from sqlalchemy.orm import Session
from app.domains.brokers.models import Broker
from app.domains.brokers.schemas import BrokerCreate

class BrokersService:
    def __init__(self, db: Session):
        self.db = db

    def create_broker(self, broker_in: BrokerCreate):
        broker = Broker(
            name=broker_in.name,
            description=broker_in.description,
            colors=broker_in.colors,
            logo=broker_in.logo,
            user_id=broker_in.user_id,
            is_active=True
        )

        self.db.add(broker)
        self.db.commit()
        self.db.refresh(broker)
        return broker