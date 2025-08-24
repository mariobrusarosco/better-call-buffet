import os
from typing import List, Dict, Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",  # Ignore extra environment variables
    )

    # CORS Configuration
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",  # React dev server
        "http://localhost:2000",  # Your custom frontend port
        "http://127.0.0.1:3000",
        "http://127.0.0.1:2000",
    ]

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

    # Sentry Configuration (Error Logging)
    SENTRY_DSN: str = ""  # Set in production environment

    # Development User ID (for mocking authentication in seeds/tests)
    MOCK_USER_ID: str = "550e8400-e29b-41d4-a716-446655440000"

    # AI Configuration
    AI_PROVIDER: str = "openai"  # "openai" or "ollama"
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-3.5-turbo-1106"
    OPENAI_TEMPERATURE: float = 0.3
    OPENAI_MAX_TOKENS: int = 4000
    
    # Ollama Configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama2"
    OLLAMA_TIMEOUT: int = 120  # seconds

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

    def get_ai_config(self) -> Dict[str, Any]:
        """Get AI configuration for the current provider"""
        if self.AI_PROVIDER.lower() == "openai":
            return {
                "provider": "openai",
                "api_key": self.OPENAI_API_KEY,
                "model": self.OPENAI_MODEL,
                "temperature": self.OPENAI_TEMPERATURE,
                "max_tokens": self.OPENAI_MAX_TOKENS
            }
        elif self.AI_PROVIDER.lower() == "ollama":
            return {
                "provider": "ollama",
                "base_url": self.OLLAMA_BASE_URL,
                "model": self.OLLAMA_MODEL,
                "timeout": self.OLLAMA_TIMEOUT
            }
        else:
            raise ValueError(f"Unsupported AI provider: {self.AI_PROVIDER}")

    def get_openai_config(self) -> Dict[str, Any]:
        """Get OpenAI configuration specifically"""
        return {
            "provider": "openai",
            "api_key": self.OPENAI_API_KEY,
            "model": self.OPENAI_MODEL,
            "temperature": self.OPENAI_TEMPERATURE,
            "max_tokens": self.OPENAI_MAX_TOKENS
        }

    def get_ollama_config(self) -> Dict[str, Any]:
        """Get Ollama configuration specifically"""
        return {
            "provider": "ollama",
            "base_url": self.OLLAMA_BASE_URL,
            "model": self.OLLAMA_MODEL,
            "timeout": self.OLLAMA_TIMEOUT
        }


settings = Settings()
