from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.domains.brokers.models import Broker


class BrokerRepository:
    """
    Repository pattern implementation for Broker entity.
    Abstracts all database operations for broker management.
    """

    def __init__(self, db: Session):
        self.db = db

    def create(self, broker_data: dict) -> Broker:
        """Create a new broker"""
        db_broker = Broker(**broker_data)
        self.db.add(db_broker)
        self.db.commit()
        self.db.refresh(db_broker)
        return db_broker

    def get_by_id_and_user(self, broker_id: UUID, user_id: UUID) -> Optional[Broker]:
        """Get a specific broker by ID and user"""
        return (
            self.db.query(Broker)
            .filter(Broker.id == broker_id, Broker.user_id == user_id)
            .first()
        )

    def get_active_brokers_by_user(self, user_id: UUID) -> List[Broker]:
        """Get all active brokers for a user"""
        return (
            self.db.query(Broker)
            .filter(Broker.user_id == user_id, Broker.is_active == True)
            .all()
        )

    def get_inactive_brokers_by_user(self, user_id: UUID) -> List[Broker]:
        """Get all inactive brokers for a user"""
        return (
            self.db.query(Broker)
            .filter(Broker.user_id == user_id, Broker.is_active == False)
            .all()
        )

    def get_all_brokers_by_user(self, user_id: UUID) -> List[Broker]:
        """Get all brokers (active and inactive) for a user"""
        return self.db.query(Broker).filter(Broker.user_id == user_id).all()

    def get_by_name_and_user(self, name: str, user_id: UUID) -> Optional[Broker]:
        """Get broker by name and user (case-insensitive)"""
        return (
            self.db.query(Broker)
            .filter(Broker.name.ilike(name), Broker.user_id == user_id)
            .first()
        )

    def exists_by_name_and_user(
        self, name: str, user_id: UUID, exclude_id: Optional[UUID] = None
    ) -> bool:
        """Check if a broker with the given name exists for a user"""
        query = self.db.query(Broker).filter(
            Broker.name.ilike(name), Broker.user_id == user_id
        )

        if exclude_id:
            query = query.filter(Broker.id != exclude_id)

        return query.first() is not None

    def update(self, broker: Broker, update_data: dict) -> Broker:
        """Update an existing broker"""
        for key, value in update_data.items():
            if hasattr(broker, key):
                setattr(broker, key, value)

        self.db.commit()
        self.db.refresh(broker)
        return broker

    def delete(self, broker: Broker) -> None:
        """Delete a broker (hard delete)"""
        self.db.delete(broker)
        self.db.commit()

    def soft_delete(self, broker: Broker) -> Broker:
        """Soft delete a broker by setting is_active to False"""
        broker.is_active = False
        self.db.commit()
        self.db.refresh(broker)
        return broker

    def reactivate(self, broker: Broker) -> Broker:
        """Reactivate a soft-deleted broker"""
        broker.is_active = True
        self.db.commit()
        self.db.refresh(broker)
        return broker

    def get_brokers_by_color(self, user_id: UUID, color: str) -> List[Broker]:
        """Get brokers that contain a specific color in their colors array"""
        return (
            self.db.query(Broker)
            .filter(
                Broker.user_id == user_id,
                Broker.colors.contains([color]),
                Broker.is_active == True,
            )
            .all()
        )

    def count_active_brokers_by_user(self, user_id: UUID) -> int:
        """Count active brokers for a user"""
        return (
            self.db.query(Broker)
            .filter(Broker.user_id == user_id, Broker.is_active == True)
            .count()
        )

    def search_brokers_by_name(self, user_id: UUID, search_term: str) -> List[Broker]:
        """Search brokers by name (case-insensitive partial match)"""
        return (
            self.db.query(Broker)
            .filter(
                Broker.user_id == user_id,
                Broker.name.ilike(f"%{search_term}%"),
                Broker.is_active == True,
            )
            .all()
        )
