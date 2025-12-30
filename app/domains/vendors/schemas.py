from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class VendorBase(BaseModel):
    name: str
    logo_url: Optional[str] = None
    website: Optional[str] = None


class VendorCreate(VendorBase):
    pass


class VendorUpdate(BaseModel):
    name: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None


class VendorResponse(VendorBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VendorFilters(BaseModel):
    # Content filters
    name_contains: Optional[str] = None
    # Sorting options
    sort_by: Optional[str] = "name"  # name, created_at
    sort_order: Optional[str] = "asc"  # asc or desc
    # Pagination
    page: int = 1
    per_page: int = 20


class VendorListMeta(BaseModel):
    total: int
    page: int = 1
    per_page: int = 20
    has_next: bool = False
    has_previous: bool = False


class VendorListResponse(BaseModel):
    data: List[VendorResponse]
    meta: VendorListMeta

    class Config:
        from_attributes = True
