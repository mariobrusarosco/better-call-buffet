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

    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"

    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Better Call Buffet"

    # Logging Configuration
    ENABLE_PERFORMANCE_LOGGING: bool = False

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT.lower() == "development"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


settings = Settings()
