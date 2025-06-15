from uuid import UUID

from app.core.constants import DEV_USER_ID


def get_current_user_id() -> UUID:
    return DEV_USER_ID
