import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.connection_and_session import Base


class CashflowView(Base):
    """A saved way of slicing the cashflow into named groups.

    View -> group -> sub-group, two levels at most. A group holds either tags
    or sub-groups; a sub-group holds tags.
    """

    __tablename__ = "cashflow_views"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
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

    # Top-level groups only; sub-groups hang off their parent. Replacing the
    # list deletes the old groups, and their sub-groups go with them
    # (parent_id ON DELETE CASCADE).
    groups = relationship(
        "CashflowViewGroup",
        primaryjoin=(
            "and_(CashflowView.id == CashflowViewGroup.view_id, "
            "CashflowViewGroup.parent_id.is_(None))"
        ),
        order_by="CashflowViewGroup.position",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (Index("ix_cashflow_views_user_id", "user_id"),)


class CashflowViewGroup(Base):
    __tablename__ = "cashflow_view_groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Set on sub-groups too, so every group of a view is one query away.
    view_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cashflow_views.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cashflow_view_groups.id", ondelete="CASCADE"),
        nullable=True,
    )
    name = Column(String(120), nullable=False)
    # "any" | "all" on groups that hold tags; NULL on groups that hold
    # sub-groups. See GroupMatch.
    match = Column(String(3), nullable=True)
    # Index among its siblings; the API exposes order, not this number.
    position = Column(Integer, nullable=False)

    groups = relationship(
        "CashflowViewGroup",
        order_by="CashflowViewGroup.position",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    tag_links = relationship(
        "CashflowViewGroupTag",
        order_by="CashflowViewGroupTag.position",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @property
    def tag_ids(self):
        return [link.tag_id for link in self.tag_links]

    __table_args__ = (
        Index("ix_cashflow_view_groups_view_position", "view_id", "position"),
        Index("ix_cashflow_view_groups_parent_id", "parent_id"),
        CheckConstraint(
            "match IS NULL OR match IN ('any', 'all')",
            name="ck_cashflow_view_groups_match",
        ),
    )


class CashflowViewGroupTag(Base):
    """Association object rather than a plain table: it carries `position`
    so tags come back in the order they were saved."""

    __tablename__ = "cashflow_view_group_tags"

    group_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cashflow_view_groups.id", ondelete="CASCADE"),
        primary_key=True,
    )
    # Deleting a tag silently drops it from every group that held it.
    tag_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )
    position = Column(Integer, nullable=False)

    __table_args__ = (
        Index("ix_cashflow_view_group_tags_tag_group", "tag_id", "group_id"),
    )
