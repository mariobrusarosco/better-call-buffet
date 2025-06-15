from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import UUID

from app.domains.users.models import User


class UserRepository:
    """
    Repository pattern implementation for User entity.
    Abstracts all database operations for user management with security considerations.
    """
    
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_data: dict) -> User:
        """Create a new user"""
        db_user = User(**user_data)
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID"""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email (case-insensitive)"""
        return self.db.query(User).filter(
            func.lower(User.email) == func.lower(email)
        ).first()

    def get_active_users(self) -> List[User]:
        """Get all active users"""
        return self.db.query(User).filter(User.is_active == True).all()

    def get_inactive_users(self) -> List[User]:
        """Get all inactive users"""
        return self.db.query(User).filter(User.is_active == False).all()

    def get_all_users(self) -> List[User]:
        """Get all users (active and inactive)"""
        return self.db.query(User).all()

    def exists_by_email(self, email: str, exclude_id: Optional[UUID] = None) -> bool:
        """Check if a user with the given email exists"""
        query = self.db.query(User).filter(
            func.lower(User.email) == func.lower(email)
        )
        
        if exclude_id:
            query = query.filter(User.id != exclude_id)
            
        return query.first() is not None

    def update(self, user: User, update_data: dict) -> User:
        """Update an existing user"""
        for key, value in update_data.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        self.db.commit()
        self.db.refresh(user)
        return user

    def deactivate(self, user: User) -> User:
        """Deactivate a user (soft delete)"""
        user.is_active = False
        self.db.commit()
        self.db.refresh(user)
        return user

    def activate(self, user: User) -> User:
        """Activate a previously deactivated user"""
        user.is_active = True
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete(self, user: User) -> None:
        """Delete a user (hard delete) - WARNING: This will cascade to related data"""
        self.db.delete(user)
        self.db.commit()

    def count_users(self, active_only: bool = True) -> int:
        """Count users"""
        query = self.db.query(User)
        if active_only:
            query = query.filter(User.is_active == True)
        return query.count()

    def search_users_by_name_or_email(self, search_term: str) -> List[User]:
        """Search users by name or email (case-insensitive partial match)"""
        search_pattern = f"%{search_term}%"
        return self.db.query(User).filter(
            User.is_active == True
        ).filter(
            func.lower(User.full_name).like(func.lower(search_pattern)) |
            func.lower(User.email).like(func.lower(search_pattern))
        ).all()

    def get_users_created_after(self, date) -> List[User]:
        """Get users created after a specific date"""
        return self.db.query(User).filter(
            User.created_at >= date,
            User.is_active == True
        ).order_by(User.created_at.desc()).all()

    def update_password(self, user: User, hashed_password: str) -> User:
        """Update user password with hashed value"""
        user.hashed_password = hashed_password
        self.db.commit()
        self.db.refresh(user)
        return user 