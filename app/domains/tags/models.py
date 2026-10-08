import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.connection_and_session import Base

transaction_tags = Table(
    "transaction_tags",
    Base.metadata,
    Column(
        "transaction_id",
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        UUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
    Index("ix_transaction_tags_tag_transaction", "tag_id", "transaction_id"),
)


subscription_tags = Table(
    "subscription_tags",
    Base.metadata,
    Column(
        "subscription_id",
        UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        UUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
    Index("ix_subscription_tags_tag_subscription", "tag_id", "subscription_id"),
)


installment_plan_tags = Table(
    "installment_plan_tags",
    Base.metadata,
    Column(
        "installment_plan_id",
        UUID(as_uuid=True),
        ForeignKey("installment_plans.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        UUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
    Index("ix_installment_plan_tags_tag_plan", "tag_id", "installment_plan_id"),
)


class TagDimension(Base):
    __tablename__ = "tag_dimensions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(100), nullable=False)
    normalized_name = Column(String(100), nullable=False)
    selection_mode = Column(String(20), nullable=False, default="multiple")
    display_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    tags = relationship("Tag", back_populates="dimension")

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "normalized_name",
            name="uq_tag_dimensions_user_normalized_name",
        ),
        CheckConstraint(
            "selection_mode IN ('single', 'multiple')",
            name="ck_tag_dimensions_selection_mode",
        ),
        Index("ix_tag_dimensions_user_active", "user_id", "is_active"),
    )


class Tag(Base):
    __tablename__ = "tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    dimension_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tag_dimensions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    name = Column(String(100), nullable=False)
    normalized_name = Column(String(100), nullable=False)
    display_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    dimension = relationship("TagDimension", back_populates="tags")
    transactions = relationship(
        "Transaction", secondary=transaction_tags, back_populates="tags"
    )
    subscriptions = relationship(
        "Subscription", secondary=subscription_tags, back_populates="tags"
    )
    installment_plans = relationship(
        "InstallmentPlan",
        secondary=installment_plan_tags,
        back_populates="tags",
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "normalized_name", name="uq_tags_user_normalized_name"
        ),
        Index("ix_tags_user_active", "user_id", "is_active"),
        Index("ix_tags_user_dimension", "user_id", "dimension_id"),
    )
