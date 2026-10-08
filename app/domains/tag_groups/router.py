from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session
from app.domains.tag_groups.schemas import (
    TagGroupCreate,
    TagGroupOverlapItem,
    TagGroupResponse,
    TagGroupSummaryItem,
    TagGroupUpdate,
)
from app.domains.tag_groups.service import TagGroupService
from app.domains.transactions.constants import MovementType

router = APIRouter()


@router.get("", response_model=List[TagGroupResponse])
def list_tag_groups(
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    service = TagGroupService(db)
    return service.build_responses(service.list_groups(user_id))


@router.post("", response_model=TagGroupResponse, status_code=status.HTTP_201_CREATED)
def create_tag_group(
    data: TagGroupCreate,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    service = TagGroupService(db)
    group = service.create_group(data, user_id)
    return service.get_group_response(group.id, user_id)


@router.get("/summary", response_model=List[TagGroupSummaryItem])
def get_tag_group_summary(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    movement_type: MovementType = Query(MovementType.EXPENSE),
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """Total and count per group over ALL matching transactions (not paginated).
    Group totals overlap by design; never add them up."""
    return TagGroupService(db).get_summary(user_id, date_from, date_to, movement_type)


@router.get("/overlaps", response_model=List[TagGroupOverlapItem])
def get_tag_group_overlaps(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    movement_type: MovementType = Query(MovementType.EXPENSE),
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """Transactions in 2+ groups, ignoring parent/child pairs. `group_ids` lists
    the most specific groups involved (an implied parent is left out)."""
    return TagGroupService(db).get_overlaps(user_id, date_from, date_to, movement_type)


@router.patch("/{group_id}", response_model=TagGroupResponse)
def update_tag_group(
    group_id: UUID,
    data: TagGroupUpdate,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    service = TagGroupService(db)
    service.update_group(group_id, data, user_id)
    return service.get_group_response(group_id, user_id)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag_group(
    group_id: UUID,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    TagGroupService(db).delete_group(group_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
