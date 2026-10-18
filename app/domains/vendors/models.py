import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    column,
    func,
    select,
    table,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import column_property, relationship

from app.db.connection_and_session import Base

# Name-only handles on the tables that reference vendors. Importing their models
# here would create a circular import (they already point back at "Vendor").
_VENDOR_REFERENCES = [
    table(name, column("vendor_id"))
    for name in ("transactions", "subscriptions", "installment_plans")
]


def _count_vendor_references(referencing_table, vendor_id: Column):
    return (
        select(func.count())
        .select_from(referencing_table)
        .where(referencing_table.c.vendor_id == vendor_id)
        .scalar_subquery()
    )


class Vendor(Base):
    __tablename__ = "vendors"
    __table_args__ = (
        Index("ix_vendors_user_id", "user_id"),
        Index("ix_vendors_name_user_id", "name", "user_id", unique=True),
    )

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    # Core Vendor Data
    name = Column(String, nullable=False)
    logo_url = Column(String, nullable=True)
    website = Column(String, nullable=True)
    # Foreign Keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    # Transactions, subscriptions and installment plans pointing at this vendor.
    # Computed by the database, never stored. Deferred so it only runs when a
    # query asks for it with undefer().
    usage_count = column_property(
        _count_vendor_references(_VENDOR_REFERENCES[0], id)
        + _count_vendor_references(_VENDOR_REFERENCES[1], id)
        + _count_vendor_references(_VENDOR_REFERENCES[2], id),
        deferred=True,
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
