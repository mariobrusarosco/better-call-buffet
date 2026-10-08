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
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.connection_and_session import Base


class AggregationView(Base):
    __tablename__ = "aggregation_views"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(120), nullable=False)
    normalized_name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    nodes = relationship(
        "AggregationNode",
        back_populates="view",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "normalized_name",
            name="uq_aggregation_views_user_normalized_name",
        ),
        Index("ix_aggregation_views_user", "user_id"),
    )


class AggregationNode(Base):
    __tablename__ = "aggregation_nodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    view_id = Column(
        UUID(as_uuid=True),
        ForeignKey("aggregation_views.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("aggregation_nodes.id", ondelete="CASCADE"),
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

    view = relationship("AggregationView", back_populates="nodes")
    parent = relationship(
        "AggregationNode",
        remote_side=[id],
        back_populates="children",
        foreign_keys=[parent_id],
    )
    children = relationship(
        "AggregationNode",
        back_populates="parent",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    conditions = relationship(
        "AggregationNodeCondition",
        back_populates="node",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index(
            "ix_aggregation_nodes_view_parent_order",
            "view_id",
            "parent_id",
            "display_order",
        ),
    )


class AggregationNodeCondition(Base):
    __tablename__ = "aggregation_node_conditions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id = Column(
        UUID(as_uuid=True),
        ForeignKey("aggregation_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    tag_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="RESTRICT"),
        nullable=False,
    )
    operator = Column(String(10), nullable=False, default="include")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    node = relationship("AggregationNode", back_populates="conditions")
    tag = relationship("Tag")

    __table_args__ = (
        UniqueConstraint(
            "node_id", "tag_id", name="uq_aggregation_node_conditions_node_tag"
        ),
        CheckConstraint(
            "operator IN ('include', 'exclude')",
            name="ck_aggregation_node_conditions_operator",
        ),
        Index("ix_aggregation_node_conditions_tag", "tag_id"),
    )
