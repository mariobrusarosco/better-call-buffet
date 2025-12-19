"""Users domain package."""

from app.core.config import get_settings


def get_current_user_id() -> str:
    """Get the current user ID for development/testing purposes."""
    return get_settings().MOCK_USER_ID
