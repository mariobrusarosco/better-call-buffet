from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, asc, desc
from sqlalchemy.orm import Session, undefer

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
        if filters:
            query = self._apply_filters(query, filters)

        # Count before loading usage and sorting: both are irrelevant to the
        # total and would make the COUNT compute usage for every vendor.
        total_count = query.count()

        query = query.options(undefer(Vendor.usage_count))
        if filters:
            query = self._apply_sorting(query, filters)
            query = self._apply_pagination(query, filters)

        return query.all(), total_count

    def _apply_filters(self, query, filters: VendorFilters):
        if filters.name_contains:
            # autoescape keeps % and _ literal instead of SQL wildcards.
            query = query.filter(
                Vendor.name.icontains(filters.name_contains, autoescape=True)
            )
        return query

    def _apply_sorting(self, query, filters: VendorFilters):
        sort_fields = {
            "name": Vendor.name,
            "created_at": Vendor.created_at,
            "usage": Vendor.usage_count,
        }

        default_field = Vendor.name
        field = sort_fields.get(filters.sort_by or "name", default_field)

        if filters.sort_order == "desc":
            query = query.order_by(desc(field))
        else:
            query = query.order_by(asc(field))
        # Stable order for ties (e.g. equal usage) so pages never shuffle.
        query = query.order_by(asc(Vendor.name), asc(Vendor.id))

        return query

    def _apply_pagination(self, query, filters: VendorFilters):
        page = max(1, filters.page)
        per_page = min(100, max(1, filters.per_page))

        offset = (page - 1) * per_page
        return query.offset(offset).limit(per_page)
