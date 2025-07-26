"""Users domain package."""

from app.core.config import settings


def get_current_user_id() -> str:
    """Get the current user ID for development/testing purposes."""
    return settings.MOCK_USER_ID
