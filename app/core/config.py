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

    def __init__(self, **kwargs):
        # Load secrets from AWS Secrets Manager in production
        if os.getenv("ENVIRONMENT") == "production":
            try:
                # Import boto3 only when needed in production
                from .secrets import get_aws_secrets

                # Get secrets from AWS Secrets Manager
                aws_secrets = get_aws_secrets("better-call-buffet/production")
                kwargs.update(aws_secrets)
            except ImportError as e:
                print(f"Warning: Could not import boto3 for secrets management: {e}")
                # Fall back to environment variables if boto3 is not available
                pass
            except Exception as e:
                print(f"Warning: Could not retrieve AWS secrets: {e}")
                # Fall back to environment variables if secrets retrieval fails
                pass

        super().__init__(**kwargs)


settings = Settings()
