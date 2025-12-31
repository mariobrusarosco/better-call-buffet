import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Date,
    Enum,
    ForeignKey,
    Index,
    String,
    DECIMAL,
    Integer,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.connection_and_session import Base


class InstallmentPlanStatus(enum.Enum):
    active = "active"
    finished = "finished"
    cancelled = "cancelled"


class InstallmentStatus(enum.Enum):
    pending = "pending"
    linked = "linked"


class InstallmentPlan(Base):
    __tablename__ = "installment_plans"
    __table_args__ = (
        Index("ix_installment_plans_user_id", "user_id"),
        Index("ix_installment_plans_credit_card_id", "credit_card_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Core Data
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    total_amount = Column(DECIMAL(15, 2), nullable=False)
    installment_count = Column(Integer, nullable=False)
    start_date = Column(Date, nullable=False) # Date of the purchase
    status = Column(Enum(InstallmentPlanStatus), default=InstallmentPlanStatus.active, nullable=False)

    # Links
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("user_categories.id"), nullable=True)
    credit_card_id = Column(UUID(as_uuid=True), ForeignKey("credit_cards.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    vendor = relationship("Vendor", foreign_keys=[vendor_id])
    category = relationship("UserCategory", foreign_keys=[category_id])
    credit_card = relationship("CreditCard", foreign_keys=[credit_card_id])
    installments = relationship("Installment", back_populates="plan", cascade="all, delete-orphan")


class Installment(Base):
    __tablename__ = "installments"
    __table_args__ = (
        Index("ix_installments_plan_id", "plan_id"),
        Index("ix_installments_due_date", "due_date"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("installment_plans.id"), nullable=False)
    
    # Core Data
    number = Column(Integer, nullable=False) # e.g. 1, 2, 3...
    amount = Column(DECIMAL(15, 2), nullable=False)
    due_date = Column(Date, nullable=False)
    status = Column(Enum(InstallmentStatus), default=InstallmentStatus.pending, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    plan = relationship("InstallmentPlan", back_populates="installments")
    transaction = relationship("Transaction", back_populates="installment", uselist=False)
