import uuid
from sqlalchemy import Column, String, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from app.db.connection_and_session import Base


class Broker(Base):
    __tablename__ = "brokers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    colors = Column(ARRAY(String), nullable=False)
    logo = Column(String, nullable=False)

    