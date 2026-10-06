from uuid import UUID
from functools import lru_cache

from app.core.config import get_settings
from app.core.ai.deprecated_client import DeprecatedAIClient

# Import JWT authentication dependency
from app.core.auth.dependencies import get_current_user_id as jwt_get_current_user_id

# Use the JWT-based authentication for getting current user ID
get_current_user_id = jwt_get_current_user_id


@lru_cache()
def get_deprecated_ai_client() -> DeprecatedAIClient:
    """Get configured deprecated AI client instance"""
    ai_config = get_settings().get_ai_config()
    return DeprecatedAIClient.from_config(ai_config)
