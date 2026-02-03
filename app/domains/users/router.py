from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user, get_current_user_id
from app.db.connection_and_session import get_db_session
from app.domains.users.schemas import User, UserUpdateIn
from app.domains.users.service import UserService

router = APIRouter()





@router.get("/me", response_model=User)
def get_current_user(
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get current user profile"""
    service = UserService(db)
    user = service.get_user_by_id(current_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user














@router.put("/me", response_model=User)
def update_current_user(
    update_data: UserUpdateIn,
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Update current user profile"""
    service = UserService(db)
    try:
        # Convert Pydantic model to dict, excluding None values and password
        update_dict = update_data.model_dump(exclude_none=True, exclude={"password"})
        user = service.update_user(current_user_id, update_dict)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))





@router.post("/change-password")
def change_password(
    current_password: str = Query(..., description="Current password"),
    new_password: str = Query(..., description="New password"),
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Change current user password"""
    service = UserService(db)
    try:
        success = service.change_password(
            current_user_id, current_password, new_password
        )
        if not success:
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        return {"message": "Password changed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))





@router.post("/authenticate")
def authenticate_user(
    email: str = Query(..., description="User email"),
    password: str = Query(..., description="User password"),
    db: Session = Depends(get_db_session),
):
    """Authenticate user with email and password"""
    service = UserService(db)
    user = service.authenticate_user(email, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    return {"message": "Authentication successful", "user_id": user.id}


@router.delete("/me")
def deactivate_current_user(
    db: Session = Depends(get_db_session),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Deactivate current user account"""
    service = UserService(db)
    user = service.deactivate_user(current_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Account deactivated successfully"}






