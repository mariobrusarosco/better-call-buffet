from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.domains.users.schemas import User, UserCreate
from app.domains.users.service import UserService

router = APIRouter()

@router.post("/", response_model=User)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db)
):
    user_service = UserService(db)
    user = user_service.get_by_email(email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists."
        )
    return user_service.create(user_in=user_in)

@router.get("/me", response_model=User)
def read_user_me(
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_user)
):
    """
    Get current user.
    Note: Authentication dependency commented out until auth system is implemented
    """
    return {"message": "To be implemented"} 