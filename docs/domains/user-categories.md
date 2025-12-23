# User Categories Domain - Implementation Guide

**Feature:** User-Defined Category Management with 2-Level Hierarchy
**Domain:** `app/domains/categories/`
**Related:** Transaction categorization, expense analytics
**See Also:** `docs/decisions/007-user-defined-categories.md`

---

## Overview

This domain manages user-defined expense categories with a 2-level hierarchy (Category → Sub-Category). Each user creates and maintains their own category structure for organizing transactions.

**Key Capabilities:**
- ✅ Create custom categories and sub-categories
- ✅ Organize categories hierarchically (max 2 levels)
- ✅ Update category names and display order
- ✅ Soft delete categories (preserve transaction history)
- ✅ Get category tree structure for UI rendering
- ✅ Auto-seed default categories for new users

---

## Database Schema

### **Table: `user_categories`**

```sql
CREATE TABLE user_categories (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Ownership
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Category Data
    name VARCHAR(100) NOT NULL,
    parent_id UUID NULL REFERENCES user_categories(id) ON DELETE CASCADE,

    -- Metadata
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT uq_user_category_name UNIQUE (user_id, name, parent_id),

    -- Indexes
    INDEX idx_user_categories_user_parent (user_id, parent_id),
    INDEX idx_user_categories_user_active (user_id, is_active)
);
```

### **Field Descriptions**

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique category identifier |
| `user_id` | UUID | Owner of this category (FK to users) |
| `name` | String(100) | Category name (e.g., "Rent", "Food") |
| `parent_id` | UUID (nullable) | NULL = top-level, UUID = sub-category |
| `display_order` | Integer | Sort order for UI (user can reorder) |
| `is_active` | Boolean | Soft delete flag (false = deleted) |
| `created_at` | Timestamp | When category was created |
| `updated_at` | Timestamp | Last modification time |

### **Hierarchy Rules**

**Top-Level Category:**
```
parent_id = NULL
Example: { name: "Rent", parent_id: null }
```

**Sub-Category:**
```
parent_id = <top-level-category-id>
Example: { name: "Family", parent_id: "rent-category-uuid" }
```

**Max Depth:** 2 levels (enforced in service layer)

### **Example Data**

```sql
-- User: 550e8400-e29b-41d4-a716-446655440000

-- Top-level categories
INSERT INTO user_categories (id, user_id, name, parent_id, display_order) VALUES
('cat-1', 'user-id', 'Housing', NULL, 1),
('cat-2', 'user-id', 'Food', NULL, 2),
('cat-3', 'user-id', 'Transportation', NULL, 3);

-- Sub-categories under Housing
INSERT INTO user_categories (id, user_id, name, parent_id, display_order) VALUES
('sub-1', 'user-id', 'Rent', 'cat-1', 1),
('sub-2', 'user-id', 'Utilities', 'cat-1', 2),
('sub-3', 'user-id', 'Maintenance', 'cat-1', 3);

-- Sub-categories under Food
INSERT INTO user_categories (id, user_id, name, parent_id, display_order) VALUES
('sub-4', 'user-id', 'Groceries', 'cat-2', 1),
('sub-5', 'user-id', 'Restaurants', 'cat-2', 2);
```

### **Update to `transactions` Table**

```sql
-- Add new foreign key column
ALTER TABLE transactions
ADD COLUMN category_id UUID NULL REFERENCES user_categories(id);

-- Create index for fast lookups
CREATE INDEX idx_transactions_category ON transactions(category_id);

-- After migration completes:
-- ALTER TABLE transactions ALTER COLUMN category_id SET NOT NULL;
-- ALTER TABLE transactions DROP COLUMN category; -- Remove old string column
```

---

## SQLAlchemy Models

### **File: `app/domains/categories/models.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.connection_and_session import Base


class UserCategory(Base):
    __tablename__ = "user_categories"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Ownership
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Category Data
    name = Column(String(100), nullable=False)
    parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user_categories.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Metadata
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    # Self-referential relationship for hierarchy
    parent = relationship(
        "UserCategory",
        remote_side=[id],
        backref="children",
        foreign_keys=[parent_id],
    )

    # Relationship to user (optional, if you want bidirectional)
    # user = relationship("User", back_populates="categories")

    # Relationship to transactions (optional)
    # transactions = relationship("Transaction", back_populates="category")

    # Database Constraints
    __table_args__ = (
        # Unique constraint: user can't have duplicate names at same level
        UniqueConstraint("user_id", "name", "parent_id", name="uq_user_category_name"),
        # Indexes for fast queries
        Index("idx_user_categories_user_parent", "user_id", "parent_id"),
        Index("idx_user_categories_user_active", "user_id", "is_active"),
    )

    def __repr__(self):
        return f"<UserCategory(id={self.id}, name='{self.name}', user_id={self.user_id})>"
```

---

## Pydantic Schemas

### **File: `app/domains/categories/schemas.py`**

```python
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class CategoryCreate(BaseModel):
    """
    Schema for creating a new category or sub-category.

    Examples:
        # Top-level category
        {
            "name": "Housing",
            "parent_id": null,
            "display_order": 1
        }

        # Sub-category
        {
            "name": "Rent",
            "parent_id": "550e8400-e29b-41d4-a716-446655440000",
            "display_order": 1
        }
    """
    name: str = Field(..., min_length=1, max_length=100, description="Category name")
    parent_id: Optional[UUID] = Field(None, description="Parent category ID (null for top-level)")
    display_order: int = Field(0, ge=0, description="Display order for sorting")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        """Validate name is not empty or whitespace-only"""
        if not v or not v.strip():
            raise ValueError("Category name cannot be empty")
        return v.strip()


class CategoryUpdate(BaseModel):
    """
    Schema for updating an existing category.

    All fields are optional - only include fields you want to update.

    Note: Changing parent_id is allowed but will be validated against max depth.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    display_order: Optional[int] = Field(None, ge=0)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        """Validate name is not empty or whitespace-only"""
        if v is not None and (not v or not v.strip()):
            raise ValueError("Category name cannot be empty")
        return v.strip() if v else v


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class CategoryResponse(BaseModel):
    """
    Basic category response (flat structure).

    Used for single category operations (create, update).
    """
    id: UUID
    user_id: UUID
    name: str
    parent_id: Optional[UUID] = None
    display_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CategoryTreeNode(BaseModel):
    """
    Hierarchical category response (tree structure).

    Used for GET /categories endpoint to render UI dropdowns.

    Example:
        {
            "id": "cat-1",
            "name": "Housing",
            "parent_id": null,
            "display_order": 1,
            "is_active": true,
            "children": [
                {
                    "id": "sub-1",
                    "name": "Rent",
                    "parent_id": "cat-1",
                    "display_order": 1,
                    "is_active": true,
                    "children": []
                },
                {
                    "id": "sub-2",
                    "name": "Utilities",
                    "parent_id": "cat-1",
                    "display_order": 2,
                    "is_active": true,
                    "children": []
                }
            ]
        }
    """
    id: UUID
    name: str
    parent_id: Optional[UUID] = None
    display_order: int
    is_active: bool
    children: List["CategoryTreeNode"] = []

    class Config:
        from_attributes = True


# ============================================================================
# BULK RESPONSE
# ============================================================================

class CategoryTreeResponse(BaseModel):
    """
    Response wrapper for GET /categories endpoint.

    Returns list of top-level categories with nested children.
    """
    categories: List[CategoryTreeNode]
    total_count: int = Field(..., description="Total number of categories (including sub-categories)")
```

---

## Repository Layer

### **File: `app/domains/categories/repository.py`**

```python
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.domains.categories.models import UserCategory


class CategoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, category_data: dict) -> UserCategory:
        """
        Create a new category.

        Args:
            category_data: Dict with user_id, name, parent_id, display_order

        Returns:
            Created UserCategory instance
        """
        category = UserCategory(**category_data)
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    def get_by_id(
        self,
        category_id: UUID,
        user_id: UUID,
        include_inactive: bool = False
    ) -> Optional[UserCategory]:
        """
        Get category by ID with ownership check.

        Args:
            category_id: Category UUID
            user_id: User UUID (ownership check)
            include_inactive: Include soft-deleted categories

        Returns:
            UserCategory or None if not found/not owned
        """
        query = self.db.query(UserCategory).filter(
            and_(
                UserCategory.id == category_id,
                UserCategory.user_id == user_id
            )
        )

        if not include_inactive:
            query = query.filter(UserCategory.is_active == True)

        return query.first()

    def get_user_categories(
        self,
        user_id: UUID,
        include_inactive: bool = False
    ) -> List[UserCategory]:
        """
        Get all categories for a user (flat list).

        Args:
            user_id: User UUID
            include_inactive: Include soft-deleted categories

        Returns:
            List of UserCategory instances, ordered by display_order
        """
        query = self.db.query(UserCategory).filter(UserCategory.user_id == user_id)

        if not include_inactive:
            query = query.filter(UserCategory.is_active == True)

        return query.order_by(UserCategory.display_order, UserCategory.name).all()

    def get_top_level_categories(
        self,
        user_id: UUID,
        include_inactive: bool = False
    ) -> List[UserCategory]:
        """
        Get only top-level categories (parent_id = NULL).

        Args:
            user_id: User UUID
            include_inactive: Include soft-deleted categories

        Returns:
            List of top-level UserCategory instances
        """
        query = self.db.query(UserCategory).filter(
            and_(
                UserCategory.user_id == user_id,
                UserCategory.parent_id == None
            )
        )

        if not include_inactive:
            query = query.filter(UserCategory.is_active == True)

        return query.order_by(UserCategory.display_order, UserCategory.name).all()

    def get_sub_categories(
        self,
        parent_id: UUID,
        user_id: UUID,
        include_inactive: bool = False
    ) -> List[UserCategory]:
        """
        Get sub-categories of a specific parent.

        Args:
            parent_id: Parent category UUID
            user_id: User UUID (ownership check)
            include_inactive: Include soft-deleted categories

        Returns:
            List of sub-category UserCategory instances
        """
        query = self.db.query(UserCategory).filter(
            and_(
                UserCategory.parent_id == parent_id,
                UserCategory.user_id == user_id
            )
        )

        if not include_inactive:
            query = query.filter(UserCategory.is_active == True)

        return query.order_by(UserCategory.display_order, UserCategory.name).all()

    def update(
        self,
        category_id: UUID,
        user_id: UUID,
        update_data: dict
    ) -> Optional[UserCategory]:
        """
        Update a category with only the fields in update_data.

        Args:
            category_id: Category UUID
            user_id: User UUID (ownership check)
            update_data: Dict of fields to update

        Returns:
            Updated UserCategory or None if not found/not owned
        """
        category = self.get_by_id(category_id, user_id)

        if not category:
            return None

        for key, value in update_data.items():
            setattr(category, key, value)

        self.db.commit()
        self.db.refresh(category)
        return category

    def soft_delete(self, category_id: UUID, user_id: UUID) -> bool:
        """
        Soft delete a category (mark is_active = False).

        Args:
            category_id: Category UUID
            user_id: User UUID (ownership check)

        Returns:
            True if deleted, False if not found/not owned
        """
        category = self.get_by_id(category_id, user_id)

        if not category:
            return False

        category.is_active = False
        self.db.commit()
        return True

    def count_transactions_using_category(
        self,
        category_id: UUID,
        user_id: UUID
    ) -> int:
        """
        Count how many transactions use this category.

        Used to prevent deletion of categories in use.

        Args:
            category_id: Category UUID
            user_id: User UUID

        Returns:
            Number of transactions using this category
        """
        from app.domains.transactions.models import Transaction

        return self.db.query(Transaction).filter(
            and_(
                Transaction.category_id == category_id,
                Transaction.user_id == user_id,
                Transaction.is_deleted == False
            )
        ).count()

    def check_duplicate_name(
        self,
        user_id: UUID,
        name: str,
        parent_id: Optional[UUID],
        exclude_category_id: Optional[UUID] = None
    ) -> bool:
        """
        Check if a category with this name already exists at this level.

        Args:
            user_id: User UUID
            name: Category name to check
            parent_id: Parent category UUID (None for top-level)
            exclude_category_id: Exclude this category ID (for updates)

        Returns:
            True if duplicate exists, False otherwise
        """
        query = self.db.query(UserCategory).filter(
            and_(
                UserCategory.user_id == user_id,
                UserCategory.name == name,
                UserCategory.parent_id == parent_id,
                UserCategory.is_active == True
            )
        )

        if exclude_category_id:
            query = query.filter(UserCategory.id != exclude_category_id)

        return query.first() is not None
```

---

## Service Layer

### **File: `app/domains/categories/service.py`**

```python
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.domains.categories.models import UserCategory
from app.domains.categories.repository import CategoryRepository
from app.domains.categories.schemas import (
    CategoryCreate,
    CategoryTreeNode,
    CategoryUpdate,
)


class CategoryService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = CategoryRepository(db)

    def create_category(
        self,
        category_data: CategoryCreate,
        user_id: UUID
    ) -> UserCategory:
        """
        Create a new category with validation.

        Validations:
        1. Parent exists and belongs to user (if parent_id provided)
        2. Parent is not a sub-category (max depth = 2)
        3. No duplicate name at same level

        Args:
            category_data: CategoryCreate schema
            user_id: UUID of user creating the category

        Returns:
            Created UserCategory instance

        Raises:
            HTTPException 404: Parent category not found
            HTTPException 400: Max depth exceeded or duplicate name
        """
        # Validate parent exists and belongs to user
        if category_data.parent_id:
            parent = self.repository.get_by_id(category_data.parent_id, user_id)
            if not parent:
                raise HTTPException(
                    status_code=404,
                    detail="Parent category not found"
                )

            # Check max depth: parent cannot have a parent (would create 3 levels)
            if parent.parent_id is not None:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot create sub-category under another sub-category (max 2 levels)"
                )

        # Check for duplicate name at same level
        if self.repository.check_duplicate_name(
            user_id=user_id,
            name=category_data.name,
            parent_id=category_data.parent_id
        ):
            level = "top-level" if category_data.parent_id is None else "sub-category"
            raise HTTPException(
                status_code=400,
                detail=f"A {level} category with name '{category_data.name}' already exists"
            )

        # Create category
        category_dict = category_data.model_dump()
        category_dict["user_id"] = user_id

        return self.repository.create(category_dict)

    def get_category_tree(self, user_id: UUID) -> List[CategoryTreeNode]:
        """
        Get user's categories as hierarchical tree structure.

        Returns top-level categories with nested children.

        Args:
            user_id: UUID of user

        Returns:
            List of CategoryTreeNode instances (top-level categories with children)
        """
        # Get all active categories for user
        all_categories = self.repository.get_user_categories(user_id)

        # Build lookup map: category_id -> category
        category_map = {cat.id: cat for cat in all_categories}

        # Build tree structure
        tree = []

        for category in all_categories:
            # Convert to CategoryTreeNode
            node = CategoryTreeNode(
                id=category.id,
                name=category.name,
                parent_id=category.parent_id,
                display_order=category.display_order,
                is_active=category.is_active,
                children=[]
            )

            if category.parent_id is None:
                # Top-level category
                tree.append(node)
            else:
                # Sub-category - add to parent's children
                parent_node = next(
                    (n for n in tree if n.id == category.parent_id),
                    None
                )
                if parent_node:
                    parent_node.children.append(node)

        # Sort top-level by display_order
        tree.sort(key=lambda x: (x.display_order, x.name))

        # Sort children by display_order
        for node in tree:
            node.children.sort(key=lambda x: (x.display_order, x.name))

        return tree

    def get_category_by_id(
        self,
        category_id: UUID,
        user_id: UUID
    ) -> UserCategory:
        """
        Get category by ID with ownership check.

        Args:
            category_id: Category UUID
            user_id: User UUID

        Returns:
            UserCategory instance

        Raises:
            HTTPException 404: Category not found or not owned by user
        """
        category = self.repository.get_by_id(category_id, user_id)
        if not category:
            raise HTTPException(
                status_code=404,
                detail="Category not found"
            )
        return category

    def update_category(
        self,
        category_id: UUID,
        user_id: UUID,
        update_data: CategoryUpdate,
    ) -> UserCategory:
        """
        Update category with validation.

        Validations:
        1. Category exists and belongs to user
        2. No duplicate name at same level (if name is changing)

        Args:
            category_id: Category UUID
            user_id: User UUID
            update_data: CategoryUpdate schema

        Returns:
            Updated UserCategory instance

        Raises:
            HTTPException 404: Category not found
            HTTPException 400: Empty update or duplicate name
        """
        # Get category with ownership check
        category = self.get_category_by_id(category_id, user_id)

        # Convert to dict (only provided fields)
        update_dict = update_data.model_dump(exclude_unset=True)

        if not update_dict:
            raise HTTPException(
                status_code=400,
                detail="No data provided to update"
            )

        # Check for duplicate name if name is changing
        if "name" in update_dict:
            if self.repository.check_duplicate_name(
                user_id=user_id,
                name=update_dict["name"],
                parent_id=category.parent_id,
                exclude_category_id=category_id
            ):
                raise HTTPException(
                    status_code=400,
                    detail=f"A category with name '{update_dict['name']}' already exists at this level"
                )

        # Update
        updated_category = self.repository.update(category_id, user_id, update_dict)
        if not updated_category:
            raise HTTPException(
                status_code=404,
                detail="Category not found"
            )

        return updated_category

    def delete_category(self, category_id: UUID, user_id: UUID) -> bool:
        """
        Soft delete a category.

        Validations:
        1. Category exists and belongs to user
        2. No transactions are using this category

        Args:
            category_id: Category UUID
            user_id: User UUID

        Returns:
            True if deleted successfully

        Raises:
            HTTPException 404: Category not found
            HTTPException 400: Category is in use by transactions
        """
        # Check category exists
        category = self.get_category_by_id(category_id, user_id)

        # Check if any transactions use this category
        transaction_count = self.repository.count_transactions_using_category(
            category_id, user_id
        )

        if transaction_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete category '{category.name}' - {transaction_count} transaction(s) are using it"
            )

        # Soft delete
        success = self.repository.soft_delete(category_id, user_id)
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Category not found"
            )

        return True
```

---

## Router Layer

### **File: `app/domains/categories/router.py`**

```python
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session
from app.domains.categories.schemas import (
    CategoryCreate,
    CategoryResponse,
    CategoryTreeNode,
    CategoryTreeResponse,
    CategoryUpdate,
)
from app.domains.categories.service import CategoryService

router = APIRouter()


@router.get("", response_model=CategoryTreeResponse)
def get_user_categories(
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    📂 Get user's category tree (hierarchical structure)

    Returns all active categories organized hierarchically:
    - Top-level categories (parent_id = null)
    - Sub-categories nested under their parents

    **Use Case:** Populate cascading dropdowns in UI

    **Response Structure:**
    ```json
    {
        "categories": [
            {
                "id": "uuid",
                "name": "Housing",
                "parent_id": null,
                "display_order": 1,
                "is_active": true,
                "children": [
                    {
                        "id": "uuid",
                        "name": "Rent",
                        "parent_id": "parent-uuid",
                        "display_order": 1,
                        "is_active": true,
                        "children": []
                    }
                ]
            }
        ],
        "total_count": 15
    }
    ```
    """
    service = CategoryService(db)
    tree = service.get_category_tree(user_id)

    # Count total categories (flatten tree)
    total_count = len(tree) + sum(len(node.children) for node in tree)

    return CategoryTreeResponse(categories=tree, total_count=total_count)


@router.post("", response_model=CategoryResponse, status_code=201)
def create_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    ➕ Create a new category or sub-category

    **Examples:**

    Create top-level category:
    ```json
    {
        "name": "Housing",
        "parent_id": null,
        "display_order": 1
    }
    ```

    Create sub-category:
    ```json
    {
        "name": "Rent",
        "parent_id": "550e8400-e29b-41d4-a716-446655440000",
        "display_order": 1
    }
    ```

    **Validations:**
    - ✅ Parent category must exist (if parent_id provided)
    - ✅ Max 2 levels (cannot create sub-sub-categories)
    - ✅ No duplicate names at same level

    **Errors:**
    - 400: Max depth exceeded or duplicate name
    - 404: Parent category not found
    """
    service = CategoryService(db)
    return service.create_category(category_data, user_id)


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(
    category_id: UUID,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    🔍 Get a single category by ID

    **Use Case:** Fetch category details for editing

    **Errors:**
    - 404: Category not found or doesn't belong to user
    """
    service = CategoryService(db)
    return service.get_category_by_id(category_id, user_id)


@router.patch("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: UUID,
    update_data: CategoryUpdate,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    ✏️ Update a category (partial update)

    Only include fields you want to update.

    **Example:**
    ```json
    {
        "name": "Housing & Utilities"
    }
    ```

    **Validations:**
    - ✅ Category must exist and belong to user
    - ✅ No duplicate names at same level (if name changing)

    **Errors:**
    - 400: Empty update or duplicate name
    - 404: Category not found
    """
    service = CategoryService(db)
    return service.update_category(category_id, user_id, update_data)


@router.delete("/{category_id}", status_code=204)
def delete_category(
    category_id: UUID,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    🗑️ Delete a category (soft delete)

    **Validation:**
    - ✅ Cannot delete if transactions are using this category

    **Behavior:**
    - Category is marked as inactive (is_active = False)
    - Not actually deleted from database (preserves history)
    - Won't appear in category tree or dropdowns

    **Errors:**
    - 400: Category is in use by transactions
    - 404: Category not found
    """
    service = CategoryService(db)
    service.delete_category(category_id, user_id)
    return None
```

---

## Default Categories Seed

### **File: `app/db/seeds/default_categories.py`**

```python
from uuid import UUID
from sqlalchemy.orm import Session
from app.domains.categories.models import UserCategory


DEFAULT_CATEGORIES = {
    "Housing": ["Rent", "Mortgage", "Utilities", "Maintenance"],
    "Food": ["Groceries", "Restaurants", "Delivery"],
    "Transportation": ["Gas", "Public Transit", "Car Payment"],
    "Personal": ["Clothing", "Health", "Entertainment"],
    "Bills": ["Phone", "Internet", "Subscriptions"],
    "Shopping": ["Electronics", "Home", "Gifts"],
    "Education": ["Courses", "Books", "Supplies"],
    "Other": ["Miscellaneous"],
}


def seed_default_categories(db: Session, user_id: UUID) -> None:
    """
    Create default categories for a new user.

    Should be called after user registration.

    Args:
        db: Database session
        user_id: UUID of newly created user
    """
    display_order = 1

    for category_name, sub_categories in DEFAULT_CATEGORIES.items():
        # Create top-level category
        top_level = UserCategory(
            user_id=user_id,
            name=category_name,
            parent_id=None,
            display_order=display_order,
        )
        db.add(top_level)
        db.flush()  # Get ID without committing

        # Create sub-categories
        for i, sub_name in enumerate(sub_categories, start=1):
            sub_category = UserCategory(
                user_id=user_id,
                name=sub_name,
                parent_id=top_level.id,
                display_order=i,
            )
            db.add(sub_category)

        display_order += 1

    db.commit()
```

---

## Integration with Transactions

### **Update Transaction Schema**

```python
# app/domains/transactions/schemas.py

class TransactionIn(TransactionBase):
    # NEW: Required UUID reference
    category_id: UUID

    # DEPRECATED: Remove after migration
    # category: str


class TransactionUpdate(BaseModel):
    # ... other fields ...
    category_id: Optional[UUID] = None

    # DEPRECATED: Remove after migration
    # category: Optional[str] = None
```

### **Update Transaction Service Validation**

```python
# app/domains/transactions/service.py

from app.domains.categories.repository import CategoryRepository

class TransactionService:
    def create_transaction(self, transaction: TransactionIn, user_id: UUID) -> Transaction:
        # ... existing code ...

        # Validate category exists and belongs to user
        category_repo = CategoryRepository(self.db)
        category = category_repo.get_by_id(transaction.category_id, user_id)
        if not category:
            raise HTTPException(
                status_code=404,
                detail="Category not found"
            )

        # ... rest of creation logic ...
```

---

## API Route Registration

### **File: `app/api/v1/router.py`**

```python
from app.domains.categories.router import router as categories_router

# Register categories router
api_router.include_router(
    categories_router,
    prefix="/categories",
    tags=["Categories"],
)
```

---

## Testing Scenarios

### **Test 1: Create Top-Level Category**

```http
POST /api/v1/categories
Authorization: Bearer <token>

{
  "name": "Housing",
  "parent_id": null,
  "display_order": 1
}

Expected: 201 Created
```

### **Test 2: Create Sub-Category**

```http
POST /api/v1/categories
Authorization: Bearer <token>

{
  "name": "Rent",
  "parent_id": "<housing-category-id>",
  "display_order": 1
}

Expected: 201 Created
```

### **Test 3: Max Depth Violation**

```http
POST /api/v1/categories
Authorization: Bearer <token>

{
  "name": "Sub-Sub-Category",
  "parent_id": "<rent-sub-category-id>",
  "display_order": 1
}

Expected: 400 Bad Request
{
  "detail": "Cannot create sub-category under another sub-category (max 2 levels)"
}
```

### **Test 4: Duplicate Name**

```http
POST /api/v1/categories
Authorization: Bearer <token>

{
  "name": "Housing",  # Already exists
  "parent_id": null,
  "display_order": 2
}

Expected: 400 Bad Request
{
  "detail": "A top-level category with name 'Housing' already exists"
}
```

### **Test 5: Get Category Tree**

```http
GET /api/v1/categories
Authorization: Bearer <token>

Expected: 200 OK
{
  "categories": [
    {
      "id": "...",
      "name": "Housing",
      "parent_id": null,
      "children": [
        { "id": "...", "name": "Rent", ... },
        { "id": "...", "name": "Utilities", ... }
      ]
    }
  ],
  "total_count": 15
}
```

### **Test 6: Delete Category with Transactions**

```http
DELETE /api/v1/categories/{id}
Authorization: Bearer <token>

Expected: 400 Bad Request
{
  "detail": "Cannot delete category 'Rent' - 42 transaction(s) are using it"
}
```

---

## Summary

**Files to Create:**
1. `app/domains/categories/models.py` - SQLAlchemy model
2. `app/domains/categories/schemas.py` - Pydantic schemas
3. `app/domains/categories/repository.py` - Data access layer
4. `app/domains/categories/service.py` - Business logic
5. `app/domains/categories/router.py` - API endpoints
6. `app/db/seeds/default_categories.py` - Seed data

**Database Migration:**
- Create `user_categories` table
- Add `category_id` to `transactions` table
- Create indexes

**API Endpoints:**
- `GET /api/v1/categories` - Get category tree
- `POST /api/v1/categories` - Create category
- `GET /api/v1/categories/{id}` - Get single category
- `PATCH /api/v1/categories/{id}` - Update category
- `DELETE /api/v1/categories/{id}` - Delete category

**Next Steps:** See `docs/guides/category-migration-strategy.md` for data migration plan.
