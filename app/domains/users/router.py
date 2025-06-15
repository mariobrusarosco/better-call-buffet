from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id  # Assuming this exists
from app.db.connection_and_session import get_db_session
from app.domains.users.schemas import User, UserIn, UserUpdateIn
from app.domains.users.service import UserService

router = APIRouter()


@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user(user_in: UserIn, db: Session = Depends(get_db_session)):
    """Create a new user"""
    service = UserService(db)
    try:
        return service.create_user(user_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[User])
def get_users(
    include_inactive: bool = Query(False, description="Include inactive users"),
    db: Session = Depends(get_db_session),
    # current_user_id: UUID = Depends(get_current_user_id)  # Admin only endpoint
):
    """Get all users (admin endpoint)"""
    service = UserService(db)
    return service.get_all_users(include_inactive)


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


@router.get("/inactive", response_model=List[User])
def get_inactive_users(
    db: Session = Depends(get_db_session),
    # current_user_id: UUID = Depends(get_current_user_id)  # Admin only endpoint
):
    """Get all inactive users (admin endpoint)"""
    service = UserService(db)
    return service.get_inactive_users()


@router.get("/search", response_model=List[User])
def search_users(
    q: str = Query(..., min_length=2, description="Search term for name or email"),
    db: Session = Depends(get_db_session),
    # current_user_id: UUID = Depends(get_current_user_id)  # Admin only endpoint
):
    """Search users by name or email (admin endpoint)"""
    service = UserService(db)
    try:
        return service.search_users(q)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/count")
def get_user_count(
    active_only: bool = Query(True, description="Count only active users"),
    db: Session = Depends(get_db_session),
    # current_user_id: UUID = Depends(get_current_user_id)  # Admin only endpoint
):
    """Get count of users (admin endpoint)"""
    service = UserService(db)
    count = service.get_user_count(active_only)
    return {"count": count, "active_only": active_only}


@router.get("/recent", response_model=List[User])
def get_recent_users(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    db: Session = Depends(get_db_session),
    # current_user_id: UUID = Depends(get_current_user_id)  # Admin only endpoint
):
    """Get recently created users (admin endpoint)"""
    service = UserService(db)
    return service.get_recent_users(days)


@router.get("/{user_id}", response_model=User)
def get_user_by_id(
    user_id: UUID,
    db: Session = Depends(get_db_session),
    # current_user_id: UUID = Depends(get_current_user_id)  # Admin only endpoint
):
    """Get user by ID (admin endpoint)"""
    service = UserService(db)
    user = service.get_user_by_id(user_id)
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


@router.put("/{user_id}", response_model=User)
def update_user_by_id(
    user_id: UUID,
    update_data: UserUpdateIn,
    db: Session = Depends(get_db_session),
    # current_user_id: UUID = Depends(get_current_user_id)  # Admin only endpoint
):
    """Update user by ID (admin endpoint)"""
    service = UserService(db)
    try:
        # Convert Pydantic model to dict, excluding None values and password
        update_dict = update_data.model_dump(exclude_none=True, exclude={"password"})
        user = service.update_user(user_id, update_dict)
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


@router.post("/{user_id}/reset-password")
def reset_user_password(
    user_id: UUID,
    new_password: str = Query(..., description="New password"),
    db: Session = Depends(get_db_session),
    # current_user_id: UUID = Depends(get_current_user_id)  # Admin only endpoint
):
    """Reset user password (admin endpoint)"""
    service = UserService(db)
    try:
        service.reset_password(user_id, new_password)
        return {"message": "Password reset successfully"}
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


@router.delete("/{user_id}")
def deactivate_user(
    user_id: UUID,
    db: Session = Depends(get_db_session),
    # current_user_id: UUID = Depends(get_current_user_id)  # Admin only endpoint
):
    """Deactivate user account (admin endpoint)"""
    service = UserService(db)
    user = service.deactivate_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deactivated successfully"}


@router.post("/{user_id}/activate", response_model=User)
def activate_user(
    user_id: UUID,
    db: Session = Depends(get_db_session),
    # current_user_id: UUID = Depends(get_current_user_id)  # Admin only endpoint
):
    """Activate a previously deactivated user (admin endpoint)"""
    service = UserService(db)
    user = service.activate_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.delete("/{user_id}/permanent")
def permanently_delete_user(
    user_id: UUID,
    db: Session = Depends(get_db_session),
    # current_user_id: UUID = Depends(get_current_user_id)  # Admin only endpoint
):
    """Permanently delete user (admin endpoint) - WARNING: This cannot be undone"""
    service = UserService(db)
    if not service.delete_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User permanently deleted"}
