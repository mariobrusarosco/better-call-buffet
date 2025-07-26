from uuid import UUID
from app.core.config import settings

# Development/testing constants
DEV_USER_ID = UUID(settings.MOCK_USER_ID)  # Configurable UUID for development user
