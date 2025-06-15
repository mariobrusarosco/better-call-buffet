"""
Logging configuration for Better Call Buffet API

This module centralizes all logging configuration to:
- Separate concerns from main app initialization
- Enable environment-specific logging behavior  
- Provide foundation for structured logging
- Make logging configuration testable
"""

import logging
import sys
from typing import Dict, Any
from app.core.config import settings


class LoggingConfig:
    """Centralized logging configuration"""
    
    @staticmethod
    def configure_logging() -> None:
        """Configure application-wide logging settings"""
        
        # Base logging configuration
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] %(levelname)s in %(name)s: %(message)s',
            stream=sys.stdout,
            force=True  # Force reconfiguration even if handlers exist
        )
        
        # Configure third-party library loggers
        LoggingConfig._configure_third_party_loggers()
        
        # Log the configuration for debugging
        logger = logging.getLogger(__name__)
        logger.info("🔧 Logging configuration initialized")
    
    @staticmethod
    def _configure_third_party_loggers() -> None:
        """Configure logging levels for third-party libraries"""
        
        # Database query logging (only warnings and errors)
        logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
        logging.getLogger('sqlalchemy.orm').setLevel(logging.WARNING)
        
        # FastAPI internal logging (only warnings and errors)
        logging.getLogger('fastapi').setLevel(logging.WARNING)
        
        # Uvicorn logging (only warnings and errors)
        logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    
    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Get a configured logger instance"""
        return logging.getLogger(name)


# For future structured logging enhancement
class StructuredLogger:
    """Foundation for structured logging with correlation IDs"""
    
    @staticmethod
    def get_structured_logger(name: str, correlation_id: str = None) -> logging.Logger:
        """Get logger with structured formatting (future implementation)"""
        # This will be enhanced when we implement structured logging
        logger = logging.getLogger(name)
        
        # Future: Add correlation ID, request context, etc.
        if correlation_id:
            # Will implement correlation ID tracking
            pass
            
        return logger


# Production-ready logging configuration (for future use)
def configure_production_logging() -> None:
    """Configure logging for production environment"""
    # Future implementation will include:
    # - JSON formatting for log aggregation
    # - Different log levels per environment
    # - Log rotation and retention policies
    # - Integration with monitoring systems
    pass


def configure_development_logging() -> None:
    """Configure logging for development environment"""
    # Enhanced developer experience with:
    # - Colored output
    # - More verbose logging
    # - SQL query logging for debugging
    pass 