from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session
from app.domains.tags.constants import MAX_TAG_LIST_LIMIT, TagSort
from app.domains.tags.schemas import TagCreate, TagResponse, TagUpdate, TagUsageResponse
from app.domains.tags.service import TagService

router = APIRouter()


@router.get("", response_model=List[TagUsageResponse])
def list_tags(
    include_inactive: bool = Query(False),
    q: Optional[str] = Query(
        None, max_length=100, description="Case-insensitive match on tag name"
    ),
    sort: TagSort = Query(
        TagSort.DISPLAY_ORDER,
        description="`usage` puts the most used tags first",
    ),
    limit: Optional[int] = Query(None, ge=1, le=MAX_TAG_LIST_LIMIT),
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    return TagService(db).list_tags(
        user_id,
        include_inactive,
        search=q,
        sort=sort,
        limit=limit,
    )


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
