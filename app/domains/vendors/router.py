from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session
from app.domains.vendors.schemas import (
    VendorCreate,
    VendorFilters,
    VendorListResponse,
    VendorResponse,
    VendorUpdate,
)
from app.domains.vendors.service import VendorService

router = APIRouter()


@router.post("", response_model=VendorResponse, status_code=201)
def create_vendor(
    vendor_in: VendorCreate,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Create a new vendor for the current user."""
    service = VendorService(db)
    try:
        return service.create_vendor(vendor_in, current_user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=VendorListResponse)
def get_vendors(
    name_contains: Optional[str] = Query(None, description="Filter by name"),
    sort_by: str = Query("name", description="Sort by field"),
    sort_order: str = Query("asc", description="Sort order (asc/desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get all vendors for the current user with filtering and pagination."""
    service = VendorService(db)
    filters = VendorFilters(
        name_contains=name_contains,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        per_page=per_page,
    )
    return service.get_vendors(current_user_id, filters)


@router.get("/{vendor_id}", response_model=VendorResponse)
def get_vendor(
    vendor_id: UUID,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get a specific vendor by ID."""
    service = VendorService(db)
    try:
        return service.get_vendor(vendor_id, current_user_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{vendor_id}", response_model=VendorResponse)
def update_vendor(
    vendor_id: UUID,
    vendor_update: VendorUpdate,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Update a vendor."""
    service = VendorService(db)
    try:
        return service.update_vendor(vendor_id, vendor_update, current_user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{vendor_id}", status_code=204)
def delete_vendor(
    vendor_id: UUID,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Delete a vendor."""
    service = VendorService(db)
    try:
        service.delete_vendor(vendor_id, current_user_id)
        return None
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
