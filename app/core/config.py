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
        # Load secrets from AWS Parameter Store in production (FREE tier service!)
        if os.getenv("ENVIRONMENT") == "production":
            try:
                # Import boto3 only when needed in production
                from .secrets import get_aws_parameter_store_secrets

                # Get secrets from AWS Parameter Store (replaces Secrets Manager for cost savings)
                aws_secrets = get_aws_parameter_store_secrets("/better-call-buffet")
                kwargs.update(aws_secrets)

                print("✅ Loaded secrets from AWS Parameter Store (Free Tier)")
            except ImportError as e:
                print(f"Warning: Could not import boto3 for secrets management: {e}")
                # Fall back to environment variables if boto3 is not available
                pass
            except Exception as e:
                print(f"Warning: Could not retrieve AWS Parameter Store secrets: {e}")
                # Fall back to environment variables if parameter retrieval fails
                pass

        super().__init__(**kwargs)


settings = Settings()
