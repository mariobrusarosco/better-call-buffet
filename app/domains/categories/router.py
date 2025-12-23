from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session
from app.domains.categories.service import CategoryService
from app.domains.categories.schemas import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryTreeNode,
)

router = APIRouter()


@router.get("", response_model=List[CategoryTreeNode])
def get_user_categories(
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    service = CategoryService(db)
    return service.assemble_category_tree(user_id)


@router.post("", response_model=CategoryResponse, status_code=201)
def create_category(
    category_in: CategoryCreate,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    service = CategoryService(db)
    category = service.create_category(category_in, user_id)
    return CategoryResponse.from_orm(category)


@router.patch("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: UUID,
    category_update: CategoryUpdate,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    service = CategoryService(db)
    data = category_update.model_dump(exclude_unset=True)

    updated_category = service.update_category(category_id, user_id, data)
    return CategoryResponse.from_orm(updated_category)


@router.delete("/{category_id}")
def delete_category(
    category_id: UUID,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    service = CategoryService(db)
    service.delete_category(category_id, user_id)

    return None
