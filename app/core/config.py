import os
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

# Only import secrets in production to avoid boto3 requirement in development
if os.getenv("ENVIRONMENT") == "production":
    from .secrets import get_aws_secrets


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

    def __init__(self, **kwargs):
        if os.getenv("ENVIRONMENT") == "production":
            # Get secrets from AWS Secrets Manager
            aws_secrets = get_aws_secrets("better-call-buffet/production")
            kwargs.update(aws_secrets)
        super().__init__(**kwargs)


settings = Settings()
