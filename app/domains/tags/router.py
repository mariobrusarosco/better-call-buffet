from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session
from app.domains.tags.schemas import (
    TagCreate,
    TagDimensionCreate,
    TagDimensionResponse,
    TagDimensionUpdate,
    TagResponse,
    TagUpdate,
)
from app.domains.tags.service import TagService

router = APIRouter()


@router.get("/dimensions", response_model=List[TagDimensionResponse])
def list_dimensions(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    return TagService(db).list_dimensions(user_id, include_inactive)


@router.post(
    "/dimensions",
    response_model=TagDimensionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_dimension(
    data: TagDimensionCreate,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    return TagService(db).create_dimension(data, user_id)


@router.patch("/dimensions/{dimension_id}", response_model=TagDimensionResponse)
def update_dimension(
    dimension_id: UUID,
    data: TagDimensionUpdate,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    return TagService(db).update_dimension(dimension_id, data, user_id)


@router.delete("/dimensions/{dimension_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dimension(
    dimension_id: UUID,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    TagService(db).delete_dimension(dimension_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("", response_model=List[TagResponse])
def list_tags(
    dimension_id: Optional[UUID] = Query(None),
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    return TagService(db).list_tags(user_id, dimension_id, include_inactive)


@router.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
def create_tag(
    data: TagCreate,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    return TagService(db).create_tag(data, user_id)


@router.patch("/{tag_id}", response_model=TagResponse)
def update_tag(
    tag_id: UUID,
    data: TagUpdate,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    return TagService(db).update_tag(tag_id, data, user_id)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(
    tag_id: UUID,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    TagService(db).delete_tag(tag_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
