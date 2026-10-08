import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.connection_and_session import Base

tag_group_tags = Table(
    "tag_group_tags",
    Base.metadata,
    Column(
        "group_id",
        UUID(as_uuid=True),
        ForeignKey("tag_groups.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        UUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
    Index("ix_tag_group_tags_tag_group", "tag_id", "group_id"),
)


class TagGroup(Base):
    """A saved tag combination. Matches transactions carrying ALL of its
    effective tags: its own plus every ancestor's."""

    __tablename__ = "tag_groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Deleting a parent deletes its whole subtree (database-level cascade).
    parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tag_groups.id", ondelete="CASCADE"),
        nullable=True,
    )
    name = Column(String(120), nullable=False)
    display_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    tags = relationship("Tag", secondary=tag_group_tags, order_by="Tag.name")

    __table_args__ = (Index("ix_tag_groups_user_parent", "user_id", "parent_id"),)
