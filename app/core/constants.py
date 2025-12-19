from uuid import UUID
from app.core.config import get_settings

# Development/testing constants
DEV_USER_ID = UUID(get_settings().MOCK_USER_ID)  # Configurable UUID for development user
