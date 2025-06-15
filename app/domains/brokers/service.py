from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.domains.brokers.models import Broker
from app.domains.brokers.schemas import BrokerIn
from app.domains.brokers.repository import BrokerRepository


class BrokersService:
    """
    Service layer for Broker business logic.
    Uses BrokerRepository for data access operations.
    """
    
    def __init__(self, db: Session):
        self.repository = BrokerRepository(db)

    def create_broker(self, broker_in: BrokerIn, user_id: UUID) -> Broker:
        """
        Create a new broker with business logic validation.
        
        Args:
            broker_in: Broker creation data
            user_id: ID of the user creating the broker
            
        Returns:
            The created broker
            
        Raises:
            ValueError: If broker name already exists for user or validation fails
        """
        # Business logic: Check if broker name already exists for this user
        if self.repository.exists_by_name_and_user(broker_in.name, user_id):
            raise ValueError(f"Broker with name '{broker_in.name}' already exists")
        
        # Business logic: Validate colors array
        if not broker_in.colors or len(broker_in.colors) == 0:
            raise ValueError("At least one color must be provided")
        
        # Business logic: Validate logo URL (basic validation)
        if not broker_in.logo or len(broker_in.logo.strip()) == 0:
            raise ValueError("Logo URL is required")
        
        # Prepare broker data
        broker_data = broker_in.model_dump()
        broker_data['user_id'] = user_id
        
        return self.repository.create(broker_data)

    def get_all_user_brokers(self, user_id: UUID) -> List[Broker]:
        """Get all active brokers for a user"""
        return self.repository.get_active_brokers_by_user(user_id)

    def get_all_user_brokers_including_inactive(self, user_id: UUID) -> List[Broker]:
        """Get all brokers (active and inactive) for a user"""
        return self.repository.get_all_brokers_by_user(user_id)

    def get_inactive_brokers(self, user_id: UUID) -> List[Broker]:
        """Get all inactive brokers for a user"""
        return self.repository.get_inactive_brokers_by_user(user_id)

    def get_broker_by_id(self, broker_id: UUID, user_id: UUID) -> Optional[Broker]:
        """
        Get broker by ID with user validation.
        
        Args:
            broker_id: ID of the broker to retrieve
            user_id: ID of the user requesting the broker
            
        Returns:
            The broker if found and belongs to user, None otherwise
        """
        return self.repository.get_by_id_and_user(broker_id, user_id)

    def update_broker(self, broker_id: UUID, user_id: UUID, update_data: dict) -> Optional[Broker]:
        """
        Update a broker with business logic validation.
        
        Args:
            broker_id: ID of the broker to update
            user_id: ID of the user updating the broker
            update_data: Dictionary of fields to update
            
        Returns:
            Updated broker if successful, None if broker not found
            
        Raises:
            ValueError: If validation fails
        """
        broker = self.repository.get_by_id_and_user(broker_id, user_id)
        if not broker:
            return None
        
        # Business logic: Check name uniqueness if name is being updated
        if 'name' in update_data:
            if self.repository.exists_by_name_and_user(update_data['name'], user_id, exclude_id=broker_id):
                raise ValueError(f"Broker with name '{update_data['name']}' already exists")
        
        # Business logic: Validate colors if being updated
        if 'colors' in update_data:
            if not update_data['colors'] or len(update_data['colors']) == 0:
                raise ValueError("At least one color must be provided")
        
        # Business logic: Validate logo if being updated
        if 'logo' in update_data:
            if not update_data['logo'] or len(update_data['logo'].strip()) == 0:
                raise ValueError("Logo URL cannot be empty")
        
        return self.repository.update(broker, update_data)

    def deactivate_broker(self, broker_id: UUID, user_id: UUID) -> Optional[Broker]:
        """
        Deactivate a broker (soft delete).
        
        Args:
            broker_id: ID of the broker to deactivate
            user_id: ID of the user deactivating the broker
            
        Returns:
            Deactivated broker if successful, None if broker not found
        """
        broker = self.repository.get_by_id_and_user(broker_id, user_id)
        if not broker:
            return None
        
        return self.repository.soft_delete(broker)

    def reactivate_broker(self, broker_id: UUID, user_id: UUID) -> Optional[Broker]:
        """
        Reactivate a previously deactivated broker.
        
        Args:
            broker_id: ID of the broker to reactivate
            user_id: ID of the user reactivating the broker
            
        Returns:
            Reactivated broker if successful, None if broker not found
        """
        broker = self.repository.get_by_id_and_user(broker_id, user_id)
        if not broker:
            return None
        
        return self.repository.reactivate(broker)

    def search_brokers(self, user_id: UUID, search_term: str) -> List[Broker]:
        """
        Search brokers by name.
        
        Args:
            user_id: ID of the user
            search_term: Term to search for in broker names
            
        Returns:
            List of matching brokers
        """
        if not search_term or len(search_term.strip()) < 2:
            raise ValueError("Search term must be at least 2 characters long")
        
        return self.repository.search_brokers_by_name(user_id, search_term.strip())

    def get_brokers_by_color(self, user_id: UUID, color: str) -> List[Broker]:
        """
        Get brokers that contain a specific color.
        
        Args:
            user_id: ID of the user
            color: Color to search for
            
        Returns:
            List of brokers containing the specified color
        """
        return self.repository.get_brokers_by_color(user_id, color)

    def get_broker_count(self, user_id: UUID) -> int:
        """
        Get count of active brokers for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Number of active brokers
        """
        return self.repository.count_active_brokers_by_user(user_id)

    def get_broker_by_name(self, name: str, user_id: UUID) -> Optional[Broker]:
        """
        Get broker by exact name (case-insensitive).
        
        Args:
            name: Name of the broker
            user_id: ID of the user
            
        Returns:
            Broker if found, None otherwise
        """
        return self.repository.get_by_name_and_user(name, user_id)