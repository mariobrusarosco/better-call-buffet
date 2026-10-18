import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.connection_and_session import Base


class CashflowView(Base):
    """A saved way of slicing the cashflow: named groups, each holding tags.
    Fixed depth (view -> groups -> tags), no nesting."""

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

    # Groups are owned by the view: replacing the list deletes the old rows.
    groups = relationship(
        "CashflowViewGroup",
        order_by="CashflowViewGroup.position",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (Index("ix_cashflow_views_user_id", "user_id"),)


class CashflowViewGroup(Base):
    __tablename__ = "cashflow_view_groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    view_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cashflow_views.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(120), nullable=False)
    # Index in the saved list; the API exposes order, not this number.
    position = Column(Integer, nullable=False)

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
