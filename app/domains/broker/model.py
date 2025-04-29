from sqlalchemy import Column, Integer, String, ARRAY
from app.db.base import Base


class Broker(Base):
    __tablename__ = "brokers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    colors = Column(ARRAY(String), nullable=False)
    logo = Column(String, nullable=False)

    