from app.core.constants import DEV_USER_ID
from uuid import UUID


def get_current_user_id() -> UUID:
    return DEV_USER_ID
