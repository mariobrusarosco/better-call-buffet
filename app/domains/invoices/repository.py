from typing import List, Optional, Dict, Any
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_
from uuid import UUID

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
        self, credit_card_id: UUID, user_id: UUID, include_deleted: bool = False
    ) -> List[Invoice]:
        """Get all invoices for a specific credit card and user"""
        query = self.db.query(Invoice).filter(
            Invoice.credit_card_id == credit_card_id, Invoice.user_id == user_id
        )

        if not include_deleted:
            query = query.filter(Invoice.is_deleted == False)

        return query.order_by(Invoice.created_at.desc()).all()

    def get_by_date_range(
        self,
        user_id: UUID,
        start_date: datetime,
        end_date: datetime,
        include_deleted: bool = False,
    ) -> List[Invoice]:
        """Get invoices within a date range for a user"""
        query = self.db.query(Invoice).filter(
            Invoice.user_id == user_id,
            Invoice.created_at >= start_date,
            Invoice.created_at <= end_date,
        )

        if not include_deleted:
            query = query.filter(Invoice.is_deleted == False)

        return query.order_by(Invoice.created_at.desc()).all()

    def search_in_raw_content(
        self, user_id: UUID, search_term: str, include_deleted: bool = False
    ) -> List[Invoice]:
        """Search invoices by content in raw_content JSON field"""
        # PostgreSQL JSON search using ->> operator for text search
        query = self.db.query(Invoice).filter(
            Invoice.user_id == user_id,
            func.cast(Invoice.raw_content, func.TEXT).ilike(f"%{search_term}%"),
        )

        if not include_deleted:
            query = query.filter(Invoice.is_deleted == False)

        return query.order_by(Invoice.created_at.desc()).all()

    def get_by_json_field(
        self, user_id: UUID, json_path: str, value: Any, include_deleted: bool = False
    ) -> List[Invoice]:
        """Get invoices where a specific JSON field matches a value"""
        # Example: json_path = "amount", value = 100.0
        # This will find invoices where raw_content->>'amount' = '100.0'
        query = self.db.query(Invoice).filter(
            Invoice.user_id == user_id,
            Invoice.raw_content.op("->>")([json_path]) == str(value),
        )

        if not include_deleted:
            query = query.filter(Invoice.is_deleted == False)

        return query.order_by(Invoice.created_at.desc()).all()

    def update(self, invoice: Invoice, update_data: dict) -> Invoice:
        """Update an existing invoice"""
        for key, value in update_data.items():
            if hasattr(invoice, key):
                setattr(invoice, key, value)

        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def soft_delete(self, invoice: Invoice) -> Invoice:
        """Soft delete an invoice by setting is_deleted to True"""
        invoice.is_deleted = True
        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def restore(self, invoice: Invoice) -> Invoice:
        """Restore a soft-deleted invoice"""
        invoice.is_deleted = False
        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def hard_delete(self, invoice: Invoice) -> None:
        """Permanently delete an invoice"""
        self.db.delete(invoice)
        self.db.commit()

    def count_by_user(self, user_id: UUID, include_deleted: bool = False) -> int:
        """Count invoices for a user"""
        query = self.db.query(Invoice).filter(Invoice.user_id == user_id)

        if not include_deleted:
            query = query.filter(Invoice.is_deleted == False)

        return query.count()

    def count_by_broker(
        self, broker_id: UUID, user_id: UUID, include_deleted: bool = False
    ) -> int:
        """Count invoices for a specific broker and user"""
        query = self.db.query(Invoice).filter(
            Invoice.broker_id == broker_id, Invoice.user_id == user_id
        )

        if not include_deleted:
            query = query.filter(Invoice.is_deleted == False)

        return query.count()

    def get_deleted_invoices(self, user_id: UUID) -> List[Invoice]:
        """Get all soft-deleted invoices for a user"""
        return (
            self.db.query(Invoice)
            .filter(Invoice.user_id == user_id, Invoice.is_deleted == True)
            .order_by(Invoice.updated_at.desc())
            .all()
        )

    def exists_for_credit_card_and_content(
        self, credit_card_id: UUID, user_id: UUID, raw_content_hash: str
    ) -> bool:
        """Check if an invoice with similar content already exists to prevent duplicates"""
        # This could be enhanced with actual content hashing
        return (
            self.db.query(Invoice)
            .filter(
                Invoice.credit_card_id == credit_card_id,
                Invoice.user_id == user_id,
                Invoice.is_deleted == False,
                func.md5(func.cast(Invoice.raw_content, func.TEXT)) == raw_content_hash,
            )
            .first()
            is not None
        )
