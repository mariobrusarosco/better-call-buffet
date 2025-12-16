from uuid import UUID
from functools import lru_cache

from app.core.config import get_settings
from app.core.ai import AIClient

# Import JWT authentication dependency
from app.core.auth.dependencies import get_current_user_id as jwt_get_current_user_id

# Use the JWT-based authentication for getting current user ID
get_current_user_id = jwt_get_current_user_id


@lru_cache()
def get_ai_client() -> AIClient:
    """Get configured AI client instance"""
    ai_config = get_settings().get_ai_config()
    return AIClient.from_config(ai_config)
