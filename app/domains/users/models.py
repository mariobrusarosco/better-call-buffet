from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.connection_and_session import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email_unique", "email", unique=True),
        Index("ix_users_created_at", "created_at"),  # Index for date-based queries
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, nullable=False, unique=True)
    full_name = Column(
        String, nullable=True
    )  # Changed from 'name' to 'full_name' to match schema
    hashed_password = Column(String, nullable=False)  # Added password field
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
