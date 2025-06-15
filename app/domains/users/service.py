from typing import List, Optional
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.domains.users.models import User
from app.domains.users.schemas import UserIn
from app.domains.users.repository import UserRepository


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    """
    Service layer for User business logic.
    Handles authentication, password management, and user operations.
    """

    def __init__(self, db: Session):
        self.repository = UserRepository(db)

    def create_user(self, user_in: UserIn) -> User:
        """
        Create a new user with business logic validation.

        Args:
            user_in: User creation data

        Returns:
            The created user

        Raises:
            ValueError: If validation fails
        """
        # Business logic: Check if email already exists
        if self.repository.exists_by_email(user_in.email):
            raise ValueError(f"User with email '{user_in.email}' already exists")

        # Business logic: Validate password strength
        if len(user_in.password) < 8:
            raise ValueError("Password must be at least 8 characters long")

        # Hash the password
        hashed_password = self.hash_password(user_in.password)

        # Prepare user data
        user_data = {
            "email": user_in.email,
            "full_name": user_in.full_name,
            "hashed_password": hashed_password,
            "is_active": user_in.is_active,
        }

        return self.repository.create(user_data)

    def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID"""
        return self.repository.get_by_id(user_id)

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email (case-insensitive)"""
        return self.repository.get_by_email(email)

    def get_all_users(self, include_inactive: bool = False) -> List[User]:
        """Get all users with optional inactive inclusion"""
        if include_inactive:
            return self.repository.get_all_users()
        else:
            return self.repository.get_active_users()

    def get_inactive_users(self) -> List[User]:
        """Get all inactive users"""
        return self.repository.get_inactive_users()

    def update_user(self, user_id: UUID, update_data: dict) -> Optional[User]:
        """
        Update a user with business logic validation.

        Args:
            user_id: ID of the user to update
            update_data: Dictionary of fields to update

        Returns:
            Updated user if successful, None if not found

        Raises:
            ValueError: If validation fails
        """
        user = self.repository.get_by_id(user_id)
        if not user:
            return None

        # Business logic: Check email uniqueness if email is being updated
        if "email" in update_data:
            if self.repository.exists_by_email(
                update_data["email"], exclude_id=user_id
            ):
                raise ValueError(
                    f"User with email '{update_data['email']}' already exists"
                )

        # Business logic: Don't allow password updates through this method
        if "password" in update_data:
            raise ValueError("Use change_password method to update passwords")

        return self.repository.update(user, update_data)

    def change_password(
        self, user_id: UUID, current_password: str, new_password: str
    ) -> bool:
        """
        Change user password with validation.

        Args:
            user_id: ID of the user
            current_password: Current password for verification
            new_password: New password

        Returns:
            True if successful, False if current password is incorrect

        Raises:
            ValueError: If validation fails
        """
        user = self.repository.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        # Verify current password
        if not self.verify_password(current_password, user.hashed_password):
            return False

        # Validate new password
        if len(new_password) < 8:
            raise ValueError("New password must be at least 8 characters long")

        # Hash and update password
        hashed_password = self.hash_password(new_password)
        self.repository.update_password(user, hashed_password)
        return True

    def reset_password(self, user_id: UUID, new_password: str) -> bool:
        """
        Reset user password (admin function).

        Args:
            user_id: ID of the user
            new_password: New password

        Returns:
            True if successful

        Raises:
            ValueError: If validation fails
        """
        user = self.repository.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        # Validate new password
        if len(new_password) < 8:
            raise ValueError("New password must be at least 8 characters long")

        # Hash and update password
        hashed_password = self.hash_password(new_password)
        self.repository.update_password(user, hashed_password)
        return True

    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate user with email and password.

        Args:
            email: User email
            password: Plain text password

        Returns:
            User if authentication successful, None otherwise
        """
        user = self.repository.get_by_email(email)
        if not user:
            return None

        if not user.is_active:
            return None

        if not self.verify_password(password, user.hashed_password):
            return None

        return user

    def deactivate_user(self, user_id: UUID) -> Optional[User]:
        """Deactivate a user (soft delete)"""
        user = self.repository.get_by_id(user_id)
        if not user:
            return None

        return self.repository.deactivate(user)

    def activate_user(self, user_id: UUID) -> Optional[User]:
        """Activate a previously deactivated user"""
        user = self.repository.get_by_id(user_id)
        if not user:
            return None

        return self.repository.activate(user)

    def delete_user(self, user_id: UUID) -> bool:
        """
        Permanently delete a user (hard delete).
        WARNING: This will cascade to related data.
        """
        user = self.repository.get_by_id(user_id)
        if not user:
            return False

        self.repository.delete(user)
        return True

    def search_users(self, search_term: str) -> List[User]:
        """
        Search users by name or email.

        Args:
            search_term: Term to search for

        Returns:
            List of matching users

        Raises:
            ValueError: If search term is too short
        """
        if not search_term or len(search_term.strip()) < 2:
            raise ValueError("Search term must be at least 2 characters long")

        return self.repository.search_users_by_name_or_email(search_term.strip())

    def get_user_count(self, active_only: bool = True) -> int:
        """Get count of users"""
        return self.repository.count_users(active_only)

    def get_recent_users(self, days: int = 30) -> List[User]:
        """Get users created in the last N days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return self.repository.get_users_created_after(cutoff_date)

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against hashed password"""
        return pwd_context.verify(plain_password, hashed_password)
