from typing import List
from uuid import UUID
from sqlalchemy.orm import Session
from app.domains.categories.repository import CategoryRepository
from app.domains.categories.models import UserCategory
from app.domains.categories.schemas import (
    CategoryCreate,
    CategoryTreeNode,
    CategoryUpdate,
    CategoryResponse,
)
from fastapi import HTTPException


class CategoryService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = CategoryRepository(db)

    def get_user_categories(self, user_id: UUID) -> List[UserCategory]:
        return self.repository.get_all_categories(user_id)

    def create_category(
        self, category_create_request: CategoryCreate, user_id: UUID
    ) -> UserCategory:
        data = {**category_create_request.model_dump(), "user_id": user_id}
        is_sub_category = data["parent_id"] is not None

        is_duplicate = self.repository.check_duplicate_name(
            user_id, data["name"], data["parent_id"]
        )

        if is_duplicate:
            if is_sub_category:
                detail = (
                    f"Sub-category '{data['name']}' already exists under this parent"
                )
            else:
                detail = f"Category '{data['name']}' already exists"

            raise HTTPException(status_code=409, detail=detail)

        if data["parent_id"] is not None:
            parent = self.repository.get_category_by_id(data["parent_id"], user_id)

            if parent is None:
                raise HTTPException(status_code=404, detail="Parent category not found")

            if parent.parent_id is not None:
                raise HTTPException(
                    status_code=400,
                    detail="Parent category is not a top level category",
                )

            if parent.is_active is False:
                raise HTTPException(
                    status_code=400, detail="Parent category is not active"
                )

        return self.repository.create_category(data)

    def assemble_category_tree(self, user_id: UUID) -> List[CategoryTreeNode]:
        categories = self.repository.get_all_categories(user_id)

        top_level_categories = [c for c in categories if c.parent_id is None]

        children_by_parent = {}
        for category in categories:
            if category.parent_id is not None:
                if category.parent_id not in children_by_parent:
                    ## Initialize the list for the parent
                    children_by_parent[category.parent_id] = []
                ## Add the child to the parent's list
                children_by_parent[category.parent_id].append(category)

        tree = []

        for top_level_category in top_level_categories:
            node = CategoryTreeNode.from_orm(top_level_category)
            children = children_by_parent.get(top_level_category.id, [])

            node.children = [CategoryTreeNode.from_orm(child) for child in children]

            tree.append(node)

        return tree

    def update_category(
        self, category_id: UUID, user_id: UUID, update_data: dict
    ) -> UserCategory:
        category = self.repository.get_category_by_id(category_id, user_id)
        if category is None:
            raise HTTPException(status_code=404, detail="Category not found")

        # Validate name change
        if "name" in update_data and update_data["name"] != category.name:
            current_parent_id = category.parent_id
            new_parent_id = update_data.get("parent_id")

            is_duplicate = self.repository.check_duplicate_name(
                user_id, update_data.get("name"), current_parent_id or new_parent_id
            )
            if is_duplicate:
                raise HTTPException(status_code=409, detail="Duplicate category name")

        if "parent_id" in update_data:
            if update_data["parent_id"] is not None:
                parent_intended = self.repository.get_category_by_id(
                    update_data.get("parent_id"), user_id
                )
                if parent_intended is None:
                    raise HTTPException(
                        status_code=404, detail="Parent category not found"
                    )
                if parent_intended.parent_id is not None:
                    raise HTTPException(
                        status_code=400,
                        detail="Parent category is not a top level category",
                    )
                if not parent_intended.is_active:
                    raise HTTPException(
                        status_code=400, detail="Parent category is not active"
                    )

        return self.repository.update_category(category, update_data)

    def delete_category(self, category_id: UUID, user_id: UUID) -> None:
        return self.repository.soft_delete_category(category_id, user_id)
