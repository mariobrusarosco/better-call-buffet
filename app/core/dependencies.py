from uuid import UUID
from functools import lru_cache

from app.core.constants import DEV_USER_ID
from app.core.config import settings
from app.core.ai import AIClient


def get_current_user_id() -> UUID:
    return DEV_USER_ID


@lru_cache()
def get_ai_client() -> AIClient:
    """Get configured AI client instance"""
    ai_config = settings.get_ai_config()
    return AIClient.from_config(ai_config)
