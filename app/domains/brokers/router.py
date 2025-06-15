from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id
from app.db.connection_and_session import get_db_session
from app.domains.brokers.schemas import BrokerIn, Broker, BrokerUpdateIn
from app.domains.brokers.service import BrokersService


router = APIRouter()


@router.get("/", response_model=List[Broker])
def get_brokers(
    include_inactive: bool = Query(False, description="Include inactive brokers in results"),
    db: Session = Depends(get_db_session), 
    user_id: UUID = Depends(get_current_user_id)
):
    """Get all brokers for the current user"""
    service = BrokersService(db)
    if include_inactive:
        return service.get_all_user_brokers_including_inactive(user_id=user_id)
    else:
        return service.get_all_user_brokers(user_id=user_id)


@router.get("/active", response_model=List[Broker])
def get_active_brokers(
    db: Session = Depends(get_db_session), 
    user_id: UUID = Depends(get_current_user_id)
):
    """Get only active brokers for the current user"""
    service = BrokersService(db)
    return service.get_all_user_brokers(user_id=user_id)


@router.get("/inactive", response_model=List[Broker])
def get_inactive_brokers(
    db: Session = Depends(get_db_session), 
    user_id: UUID = Depends(get_current_user_id)
):
    """Get only inactive brokers for the current user"""
    service = BrokersService(db)
    return service.get_inactive_brokers(user_id=user_id)


@router.get("/search", response_model=List[Broker])
def search_brokers(
    q: str = Query(..., min_length=2, description="Search term for broker names"),
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id)
):
    """Search brokers by name"""
    service = BrokersService(db)
    try:
        return service.search_brokers(user_id, q)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/by-color/{color}", response_model=List[Broker])
def get_brokers_by_color(
    color: str,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get brokers that contain a specific color"""
    service = BrokersService(db)
    return service.get_brokers_by_color(user_id, color)


@router.get("/count")
def get_broker_count(
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get count of active brokers"""
    service = BrokersService(db)
    count = service.get_broker_count(user_id)
    return {"count": count}


@router.post("/", response_model=Broker)
def create_broker(
    broker_in: BrokerIn, 
    db: Session = Depends(get_db_session), 
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Create a new broker"""
    service = BrokersService(db)
    try:
        return service.create_broker(broker_in=broker_in, user_id=current_user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{broker_id}", response_model=Broker)
def get_broker_by_id(
    broker_id: UUID,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get a specific broker by ID"""
    service = BrokersService(db)
    broker = service.get_broker_by_id(broker_id, user_id)
    if not broker:
        raise HTTPException(status_code=404, detail="Broker not found")
    return broker


@router.put("/{broker_id}", response_model=Broker)
def update_broker(
    broker_id: UUID,
    update_data: BrokerUpdateIn,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id)
):
    """Update a broker"""
    service = BrokersService(db)
    try:
        # Convert Pydantic model to dict, excluding None values
        update_dict = update_data.model_dump(exclude_none=True)
        broker = service.update_broker(broker_id, user_id, update_dict)
        if not broker:
            raise HTTPException(status_code=404, detail="Broker not found")
        return broker
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{broker_id}")
def deactivate_broker(
    broker_id: UUID,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id)
):
    """Deactivate a broker (soft delete)"""
    service = BrokersService(db)
    broker = service.deactivate_broker(broker_id, user_id)
    if not broker:
        raise HTTPException(status_code=404, detail="Broker not found")
    return {"message": "Broker deactivated successfully"}


@router.post("/{broker_id}/reactivate", response_model=Broker)
def reactivate_broker(
    broker_id: UUID,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id)
):
    """Reactivate a previously deactivated broker"""
    service = BrokersService(db)
    broker = service.reactivate_broker(broker_id, user_id)
    if not broker:
        raise HTTPException(status_code=404, detail="Broker not found")
    return broker


@router.get("/name/{name}", response_model=Broker)
def get_broker_by_name(
    name: str,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get broker by exact name (case-insensitive)"""
    service = BrokersService(db)
    broker = service.get_broker_by_name(name, user_id)
    if not broker:
        raise HTTPException(status_code=404, detail="Broker not found")
    return broker