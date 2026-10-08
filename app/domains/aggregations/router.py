from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session
from app.domains.aggregations.schemas import (
    AggregationNodeCreate,
    AggregationNodeUpdate,
    AggregationViewCreate,
    AggregationViewResponse,
    AggregationViewResult,
    AggregationViewSummaryResponse,
    AggregationViewUpdate,
)
from app.domains.aggregations.service import AggregationService
from app.domains.transactions.constants import MovementType

router = APIRouter()


@router.get("/views", response_model=List[AggregationViewSummaryResponse])
def list_views(
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    return AggregationService(db).list_views(user_id)


@router.post(
    "/views",
    response_model=AggregationViewSummaryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_view(
    data: AggregationViewCreate,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    return AggregationService(db).create_view(data, user_id)


@router.get("/views/{view_id}", response_model=AggregationViewResponse)
def get_view(
    view_id: UUID,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    return AggregationService(db).get_view_response(view_id, user_id)


@router.patch("/views/{view_id}", response_model=AggregationViewSummaryResponse)
def update_view(
    view_id: UUID,
    data: AggregationViewUpdate,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    return AggregationService(db).update_view(view_id, data, user_id)


@router.delete("/views/{view_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_view(
    view_id: UUID,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    AggregationService(db).delete_view(view_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/views/{view_id}/nodes",
    response_model=AggregationViewResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_node(
    view_id: UUID,
    data: AggregationNodeCreate,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    return AggregationService(db).create_node(view_id, data, user_id)


@router.patch(
    "/views/{view_id}/nodes/{node_id}", response_model=AggregationViewResponse
)
def update_node(
    view_id: UUID,
    node_id: UUID,
    data: AggregationNodeUpdate,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    return AggregationService(db).update_node(view_id, node_id, data, user_id)


@router.delete(
    "/views/{view_id}/nodes/{node_id}", response_model=AggregationViewResponse
)
def delete_node(
    view_id: UUID,
    node_id: UUID,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    return AggregationService(db).delete_node(view_id, node_id, user_id)


@router.get("/views/{view_id}/results", response_model=AggregationViewResult)
def get_results(
    view_id: UUID,
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    movement_type: Optional[List[MovementType]] = Query(None),
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    return AggregationService(db).get_results(
        view_id,
        user_id,
        date_from=date_from,
        date_to=date_to,
        movement_types=movement_type,
    )
