from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.error_handlers import NotFoundError, ValidationError
from app.core.logging_config import get_logger
from app.domains.vendors.models import Vendor
from app.domains.vendors.repository import VendorRepository
from app.domains.vendors.schemas import (
    VendorCreate,
    VendorFilters,
    VendorListMeta,
    VendorListResponse,
    VendorResponse,
    VendorUpdate,
)

logger = get_logger(__name__)


class VendorService:
    def __init__(self, db: Session):
        self.repository = VendorRepository(db)

    def create_vendor(self, vendor_data: VendorCreate, user_id: UUID) -> Vendor:
        # Check for duplicates
        if self.repository.get_by_name(vendor_data.name, user_id):
            raise ValidationError(
                message=f"Vendor with name '{vendor_data.name}' already exists.",
                error_code="VENDOR_ALREADY_EXISTS",
            )

        vendor = Vendor(
            name=vendor_data.name,
            logo_url=vendor_data.logo_url,
            website=vendor_data.website,
            user_id=user_id,
        )
        return self.repository.create(vendor)

    def get_vendor(self, vendor_id: UUID, user_id: UUID) -> Vendor:
        vendor = self.repository.get_by_id(vendor_id, user_id)
        if not vendor:
            raise NotFoundError(
                message=f"Vendor with ID {vendor_id} not found",
                error_code="VENDOR_NOT_FOUND",
            )
        return vendor

    def update_vendor(
        self, vendor_id: UUID, vendor_data: VendorUpdate, user_id: UUID
    ) -> Vendor:
        vendor = self.get_vendor(vendor_id, user_id)

        # Check name uniqueness if name is changing
        if (
            vendor_data.name
            and vendor_data.name != vendor.name
            and self.repository.get_by_name(vendor_data.name, user_id)
        ):
            raise ValidationError(
                message=f"Vendor with name '{vendor_data.name}' already exists.",
                error_code="VENDOR_ALREADY_EXISTS",
            )

        update_data = vendor_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(vendor, key, value)

        return self.repository.update(vendor)

    def delete_vendor(self, vendor_id: UUID, user_id: UUID) -> None:
        vendor = self.get_vendor(vendor_id, user_id)
        # TODO: Add check for linked subscriptions/transactions when those features exist
        self.repository.delete(vendor)

    def get_vendors(
        self, user_id: UUID, filters: Optional[VendorFilters] = None
    ) -> VendorListResponse:
        if filters is None:
            filters = VendorFilters()

        # Validate pagination
        filters.page = max(1, filters.page)
        filters.per_page = min(100, max(1, filters.per_page))

        vendors, total_count = self.repository.get_all_with_filters(user_id, filters)

        # Calculate pagination metadata
        total_pages = (total_count + filters.per_page - 1) // filters.per_page
        has_next = filters.page < total_pages
        has_previous = filters.page > 1

        vendor_responses = [VendorResponse.from_orm(v) for v in vendors]

        meta = VendorListMeta(
            total=total_count,
            page=filters.page,
            per_page=filters.per_page,
            has_next=has_next,
            has_previous=has_previous,
        )

        return VendorListResponse(data=vendor_responses, meta=meta)
