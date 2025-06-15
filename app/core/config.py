import os
from typing import List

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings

# Only import secrets in production to avoid boto3 requirement in development
if os.getenv("ENVIRONMENT") == "production":
    from .secrets import get_aws_secrets


class Settings(BaseSettings):
    API_V1_PREFIX: str
    PROJECT_NAME: str
    BACKEND_CORS_ORIGINS: List[str] = []

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database
    DATABASE_URL: str

    # Optional
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True

    def __init__(self, **kwargs):
        if os.getenv("ENVIRONMENT") == "production":
            # Get secrets from AWS Secrets Manager
            aws_secrets = get_aws_secrets("better-call-buffet/production")
            kwargs.update(aws_secrets)
        super().__init__(**kwargs)


settings = Settings()
