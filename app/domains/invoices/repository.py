from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.domains.invoices.models import Invoice


class InvoiceRepository:
    """
    Repository pattern implementation for Invoice entity.
    Abstracts all database operations for invoice management with JSON content handling.
    """

    def __init__(self, db: Session):
        self.db = db

    def create(self, invoice_data: dict) -> Invoice:
        """Create a new invoice"""
        db_invoice = Invoice(**invoice_data)
        self.db.add(db_invoice)
        self.db.commit()
        self.db.refresh(db_invoice)
        return db_invoice

    def get_by_id_and_user(
        self, invoice_id: UUID, user_id: UUID, include_deleted: bool = False
    ) -> Optional[Invoice]:
        """Get a specific invoice by ID and user"""
        query = self.db.query(Invoice).filter(
            Invoice.id == invoice_id, Invoice.user_id == user_id
        )

        if not include_deleted:
            query = query.filter(Invoice.is_deleted == False)

        return query.first()

    def get_by_user(
        self, user_id: UUID, include_deleted: bool = False
    ) -> List[Invoice]:
        """Get all invoices for a user"""
        query = self.db.query(Invoice).filter(Invoice.user_id == user_id)

        if not include_deleted:
            query = query.filter(Invoice.is_deleted == False)

        return query.order_by(Invoice.created_at.desc()).all()

    def get_by_broker_and_user(
        self, broker_id: UUID, user_id: UUID, include_deleted: bool = False
    ) -> List[Invoice]:
        """Get all invoices for a specific broker and user"""
        query = self.db.query(Invoice).filter(
            Invoice.broker_id == broker_id, Invoice.user_id == user_id
        )

        if not include_deleted:
            query = query.filter(Invoice.is_deleted == False)

        return query.order_by(Invoice.created_at.desc()).all()

    def get_by_credit_card_and_user(
        self,
        credit_card_id: UUID,
        user_id: UUID,
        include_deleted: bool = False,
        page: int = 1,
        per_page: int = 10,
    ) -> List[Invoice]:
        """Get all invoices for a specific credit card and user with pagination"""
        query = self.db.query(Invoice).filter(
            Invoice.credit_card_id == credit_card_id, Invoice.user_id == user_id
        )

        if not include_deleted:
            query = query.filter(Invoice.is_deleted == False)

        # Apply ordering first (required before pagination)
        query = query.order_by(Invoice.created_at.desc())

        # Apply pagination if requested
        if page and per_page:
            offset = (page - 1) * per_page
            query = query.offset(offset).limit(per_page)

        return query.all()
