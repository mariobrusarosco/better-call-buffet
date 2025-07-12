import os
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",  # Ignore extra environment variables
    )

    # CORS Configuration
    BACKEND_CORS_ORIGINS: List[str] = []

    # Database - provide test default for CI
    DATABASE_URL: str = "sqlite:///./test.db"

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Logging Configuration
    ENABLE_PERFORMANCE_LOGGING: bool = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


settings = Settings()
