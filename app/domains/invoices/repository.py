from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, asc, desc, func, or_
from sqlalchemy.orm import Session

from app.domains.invoices.models import Invoice
from app.domains.invoices.schemas import InvoiceFilters


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

    def get_by_id(self, invoice_id: UUID, user_id: UUID) -> Optional[Invoice]:
        """Get a specific invoice by ID"""
        return (
            self.db.query(Invoice)
            .filter(and_(Invoice.id == invoice_id, Invoice.user_id == user_id))
            .first()
        )

    def get_all_by_user(self, user_id: UUID) -> List[Invoice]:
        """Get all invoices for a specific user"""
        return (
            self.db.query(Invoice)
            .filter(Invoice.user_id == user_id)
            .order_by(Invoice.created_at.desc())
            .all()
        )

    # 🎓 NEW STRUCTURED FILTERING METHODS
    def get_invoices_with_filters(
        self,
        user_id: UUID,
        filters: Optional[InvoiceFilters] = None,
    ) -> Tuple[List[Invoice], int]:
        """
        Get invoices using structured filters.

        Benefits:
        - ✅ Consistent filtering interface
        - ✅ Easy to extend with new filter options
        - ✅ Type-safe filter validation
        - ✅ Embedded pagination handling
        """
        # Base query
        query = self.db.query(Invoice).filter(Invoice.user_id == user_id)

        # Apply structured filters
        if filters:
            query = self._apply_filters(query, filters)
            query = self._apply_sorting(query, filters)

            # Get total count before pagination
            total_count = query.count()

            # Apply pagination
            query = self._apply_pagination(query, filters)
        else:
            total_count = query.count()

        return query.all(), total_count

    def get_credit_card_invoices_with_filters(
        self,
        credit_card_id: UUID,
        user_id: UUID,
        filters: Optional[InvoiceFilters] = None,
    ) -> Tuple[List[Invoice], int]:
        """
        Get invoices for a specific credit card using structured filters.
        """
        # Base query
        query = self.db.query(Invoice).filter(
            and_(
                Invoice.credit_card_id == credit_card_id,
                Invoice.user_id == user_id,
            )
        )

        # Apply structured filters
        if filters:
            query = self._apply_filters(query, filters)
            query = self._apply_sorting(query, filters)

            # Get total count before pagination
            total_count = query.count()

            # Apply pagination
            query = self._apply_pagination(query, filters)
        else:
            total_count = query.count()

        return query.all(), total_count

    def get_broker_invoices_with_filters(
        self,
        broker_id: UUID,
        user_id: UUID,
        filters: Optional[InvoiceFilters] = None,
    ) -> Tuple[List[Invoice], int]:
        """
        Get invoices for a specific broker using structured filters.
        """
        # Base query
        query = self.db.query(Invoice).filter(
            and_(
                Invoice.broker_id == broker_id,
                Invoice.user_id == user_id,
            )
        )

        # Apply structured filters
        if filters:
            query = self._apply_filters(query, filters)
            query = self._apply_sorting(query, filters)

            # Get total count before pagination
            total_count = query.count()

            # Apply pagination
            query = self._apply_pagination(query, filters)
        else:
            total_count = query.count()

        return query.all(), total_count

    def _apply_filters(self, query, filters: InvoiceFilters):
        """🔧 Private method to build WHERE conditions dynamically"""
        # Resource filters
        if filters.credit_card_id:
            query = query.filter(Invoice.credit_card_id == filters.credit_card_id)
        if filters.broker_id:
            query = query.filter(Invoice.broker_id == filters.broker_id)

        # Status filters
        if filters.is_paid is not None:
            query = query.filter(Invoice.is_paid == filters.is_paid)
        if filters.is_deleted is not None:
            query = query.filter(Invoice.is_deleted == filters.is_deleted)

        # Date range filters
        if filters.date_from:
            query = query.filter(Invoice.created_at >= filters.date_from)
        if filters.date_to:
            query = query.filter(Invoice.created_at <= filters.date_to)

        # Amount filters (from raw_invoice total_due)
        # TODO: Implement amount filtering with proper JSON handling
        # For now, skip amount filtering to avoid complex JSON casting
        if filters.amount_min is not None or filters.amount_max is not None:
            # Log that amount filtering is not yet implemented
            pass

        # Period filter
        if filters.period_contains:
            query = query.filter(
                Invoice.raw_invoice["period"]
                .as_string()
                .ilike(f"%{filters.period_contains}%")
            )

        return query

    def _apply_sorting(self, query, filters: InvoiceFilters):
        """🔧 Apply sorting based on filter preferences"""
        sort_fields = {
            "created_at": Invoice.created_at,
            "updated_at": Invoice.updated_at,
            "is_paid": Invoice.is_paid,
        }

        field = sort_fields.get(filters.sort_by or "created_at", Invoice.created_at)

        if filters.sort_order == "asc":
            query = query.order_by(asc(field))
        else:
            # Default to desc, with secondary sort by created_at desc
            query = query.order_by(desc(field), desc(Invoice.created_at))

        return query

    def _apply_pagination(self, query, filters: InvoiceFilters):
        """🔧 Apply pagination based on filter preferences"""
        page = max(1, filters.page)
        per_page = min(100, max(1, filters.per_page))

        offset = (page - 1) * per_page
        return query.offset(offset).limit(per_page)

    # 🔄 LEGACY METHODS (for backward compatibility)
    def get_by_broker_and_user(
        self, broker_id: UUID, user_id: UUID, include_deleted: bool = False
    ) -> List[Invoice]:
        """LEGACY METHOD - Use get_broker_invoices_with_filters instead."""
        filters = InvoiceFilters(
            broker_id=broker_id,
            is_deleted=include_deleted,
            page=1,
            per_page=999999,  # Large number to get all
        )
        invoices, _ = self.get_broker_invoices_with_filters(broker_id, user_id, filters)
        return invoices

    def get_by_credit_card_and_user(
        self,
        credit_card_id: UUID,
        user_id: UUID,
        include_deleted: bool = False,
        page: int = 1,
        per_page: int = 10,
    ) -> List[Invoice]:
        """LEGACY METHOD - Use get_credit_card_invoices_with_filters instead."""
        filters = InvoiceFilters(
            credit_card_id=credit_card_id,
            is_deleted=include_deleted,
            page=page,
            per_page=per_page,
        )
        invoices, _ = self.get_credit_card_invoices_with_filters(
            credit_card_id, user_id, filters
        )
        return invoices
