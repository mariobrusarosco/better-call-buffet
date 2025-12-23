from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, field_validator

class CategoryCreate(BaseModel):
    """Input for creating a category"""
    name: str
    parent_id: Optional[UUID] = None
    display_order: int = 0

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure category name is not empty"""
        if not v or not v.strip():
            raise ValueError("Category name cannot be empty")
        return v.strip()


class CategoryUpdate(BaseModel):
    """Input for updating a category"""
    name: Optional[str] = None
    parent_id: Optional[UUID] = None
    display_order: Optional[int] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Ensure category name is not empty if provided"""
        if v is not None and (not v or not v.strip()):
            raise ValueError("Category name cannot be empty")
        return v.strip() if v else v

    @field_validator("display_order")
    @classmethod
    def validate_display_order(cls, v: Optional[int]) -> Optional[int]:
        """Ensure display order is not negative if provided"""
        if v is not None and v < 0:
            raise ValueError("Display order cannot be negative")
        return v


class CategoryResponse(BaseModel):
    """Single category"""
    id: UUID
    name: str
    parent_id: Optional[UUID] = None
    display_order: int
    is_active: bool

    class Config:
        from_attributes = True  # Enable conversion from SQLAlchemy models


class CategoryTreeNode(CategoryResponse):
    """Category tree (with children)"""
    children: List["CategoryTreeNode"] = []
