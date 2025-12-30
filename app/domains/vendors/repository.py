from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, asc, desc
from sqlalchemy.orm import Session

from app.domains.vendors.models import Vendor
from app.domains.vendors.schemas import VendorFilters


class VendorRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, vendor: Vendor) -> Vendor:
        self.db.add(vendor)
        self.db.commit()
        self.db.refresh(vendor)
        return vendor

    def get_by_id(self, vendor_id: UUID, user_id: UUID) -> Optional[Vendor]:
        return (
            self.db.query(Vendor)
            .filter(and_(Vendor.id == vendor_id, Vendor.user_id == user_id))
            .first()
        )

    def get_by_name(self, name: str, user_id: UUID) -> Optional[Vendor]:
        return (
            self.db.query(Vendor)
            .filter(and_(Vendor.name == name, Vendor.user_id == user_id))
            .first()
        )

    def update(self, vendor: Vendor) -> Vendor:
        self.db.commit()
        self.db.refresh(vendor)
        return vendor

    def delete(self, vendor: Vendor) -> None:
        self.db.delete(vendor)
        self.db.commit()

    def get_all_with_filters(
        self, user_id: UUID, filters: Optional[VendorFilters] = None
    ) -> Tuple[List[Vendor], int]:
        # Base query
        query = self.db.query(Vendor).filter(Vendor.user_id == user_id)

        # Apply structured filters
        if filters:
            query = self._apply_filters(query, filters)
            query = self._apply_sorting(query, filters)

            total_count = query.count()
            query = self._apply_pagination(query, filters)
        else:
            total_count = query.count()

        return query.all(), total_count

    def _apply_filters(self, query, filters: VendorFilters):
        if filters.name_contains:
            query = query.filter(Vendor.name.ilike(f"%{filters.name_contains}%"))
        return query

    def _apply_sorting(self, query, filters: VendorFilters):
        sort_fields = {
            "name": Vendor.name,
            "created_at": Vendor.created_at,
        }

        default_field = Vendor.name
        field = sort_fields.get(filters.sort_by or "name", default_field)

        if filters.sort_order == "desc":
            query = query.order_by(desc(field))
        else:
            query = query.order_by(asc(field))

        return query

    def _apply_pagination(self, query, filters: VendorFilters):
        page = max(1, filters.page)
        per_page = min(100, max(1, filters.per_page))

        offset = (page - 1) * per_page
        return query.offset(offset).limit(per_page)
