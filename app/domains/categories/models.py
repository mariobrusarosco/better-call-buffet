import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.connection_and_session import Base


class UserCategory(Base):
    """
    User-defined categories for transaction organization.

    Supports 2-level hierarchy:
    - Top-level: parent_id = NULL (e.g., "Housing", "Food")
    - Sub-category: parent_id = UUID (e.g., "Rent" under "Housing")
    """

    __tablename__ = "user_categories"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(100), nullable=False)
    parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user_categories.id", ondelete="CASCADE"),
        nullable=True,
    )
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships - self-referential for hierarchy
    parent = relationship(
        "UserCategory",
        remote_side=[id],
        backref="children",
        foreign_keys=[parent_id],
    )

    # Database Constraints
    __table_args__ = (
        UniqueConstraint("user_id", "name", "parent_id", name="uq_user_category_name"),
        Index("idx_user_categories_user_parent", "user_id", "parent_id"),
        Index("idx_user_categories_user_active", "user_id", "is_active"),
    )

    def __repr__(self):
        return (
            f"<UserCategory(id={self.id}, name='{self.name}', user_id={self.user_id})>"
        )
