"""
🎓 Structured Logging Configuration

This module provides comprehensive structured logging setup for the FastAPI application,
enabling JSON-formatted logs with correlation IDs, performance metrics, and contextual information.

Educational Focus:
- Structured logging benefits and JSON format advantages
- Context management and correlation ID propagation
- Environment-specific configuration
- Performance monitoring through logs
"""

import json
import logging
import logging.config
import sys
import time
from contextvars import ContextVar
from typing import Any, Dict, Optional
from uuid import uuid4

import structlog

# ============================================================================
# 🎓 CONTEXT VARIABLES FOR REQUEST TRACKING
# ============================================================================

# Context variables for storing request-specific information
# These persist across async calls within the same request
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
request_start_time_var: ContextVar[Optional[float]] = ContextVar(
    "request_start_time", default=None
)


# ============================================================================
# 🎓 CUSTOM JSON FORMATTER
# ============================================================================


class EnhancedJSONFormatter(logging.Formatter):
    """
    🎓 Enhanced JSON formatter that adds contextual information to every log entry.

    Educational Note:
    This formatter automatically enriches log entries with request context,
    making it easy to trace requests and understand performance characteristics.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON with additional context"""
        # Create base log entry
        log_entry = {
            "timestamp": time.strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ", time.gmtime(record.created)
            ),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
            "service": "better-call-buffet",
        }

        # Add request context if available
        request_id = request_id_var.get()
        if request_id:
            log_entry["request_id"] = request_id

        user_id = user_id_var.get()
        if user_id:
            log_entry["user_id"] = user_id

        # Add performance information
        start_time = request_start_time_var.get()
        if start_time is not None:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            log_entry["duration_ms"] = duration_ms

        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add any extra fields from the log record
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)

        return json.dumps(log_entry, default=str)


# ============================================================================
# 🎓 LOGGING CONFIGURATION
# ============================================================================


def setup_logging(environment: str = "development", log_level: str = "INFO") -> None:
    """
    🎓 Configure structured logging for the application.

    Educational Note:
    This function sets up both standard Python logging and structlog for optimal
    developer experience and production monitoring capabilities.

    Args:
        environment: The application environment (development/staging/production)
        log_level: The minimum log level to capture
    """

    # Configure standard logging with JSON formatter
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": EnhancedJSONFormatter,
            },
            "standard": {
                "format": "[%(asctime)s] %(levelname)s in %(name)s: %(message)s"
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json" if environment == "production" else "standard",
                "stream": sys.stdout,
                "level": log_level.upper(),
            }
        },
        "root": {"level": log_level.upper(), "handlers": ["console"]},
        "loggers": {
            # FastAPI and Uvicorn loggers
            "uvicorn": {"level": "INFO", "propagate": True},
            "uvicorn.access": {"level": "INFO", "propagate": True},
            "fastapi": {"level": "INFO", "propagate": True},
            # SQLAlchemy logging for database operations
            "sqlalchemy.engine": {
                "level": "INFO" if environment == "development" else "WARNING",
                "propagate": True,
            },
            "sqlalchemy.pool": {"level": "WARNING", "propagate": True},
            # Application loggers
            "app": {"level": log_level.upper(), "propagate": True},
        },
    }

    # Apply logging configuration
    logging.config.dictConfig(logging_config)

    # Configure structlog for enhanced logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            (
                structlog.processors.JSONRenderer()
                if environment == "production"
                else structlog.dev.ConsoleRenderer(colors=True)
            ),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Log the configuration setup
    logger = structlog.get_logger("app.logging")
    logger.info(
        "Structured logging configured",
        environment=environment,
        log_level=log_level,
        json_format=environment == "production",
    )


# ============================================================================
# 🎓 CONTEXT MANAGEMENT UTILITIES
# ============================================================================


def set_request_context(
    request_id: Optional[str] = None, user_id: Optional[str] = None
) -> str:
    """
    🎓 Set request context for logging.

    Educational Note:
    This function establishes the context for a request, allowing all subsequent
    log entries to automatically include request and user information.

    Args:
        request_id: Unique identifier for the request (generated if not provided)
        user_id: Identifier for the authenticated user

    Returns:
        The request ID that was set
    """
    # Generate request ID if not provided
    if request_id is None:
        request_id = str(uuid4())

    # Set context variables
    request_id_var.set(request_id)
    if user_id:
        user_id_var.set(user_id)
    request_start_time_var.set(time.time())

    return request_id


def clear_request_context() -> None:
    """Clear request context after request completion"""
    request_id_var.set(None)
    user_id_var.set(None)
    request_start_time_var.set(None)


def get_request_id() -> Optional[str]:
    """Get the current request ID from context"""
    return request_id_var.get()


def get_user_id() -> Optional[str]:
    """Get the current user ID from context"""
    return user_id_var.get()


# ============================================================================
# 🎓 STRUCTURED LOGGER FACTORY
# ============================================================================


def get_logger(name: str) -> structlog.BoundLogger:
    """
    🎓 Get a structured logger instance.

    Educational Note:
    This factory function returns a structured logger that automatically
    includes request context in all log entries, making debugging much easier.

    Usage:
        logger = get_logger(__name__)
        logger.info("User action performed", action="create_account", account_id=123)
    """
    return structlog.get_logger(name)


# ============================================================================
# 🎓 PERFORMANCE LOGGING UTILITIES
# ============================================================================


class PerformanceTimer:
    """
    🎓 Context manager for timing operations and logging performance metrics.

    Usage:
        with PerformanceTimer("database_query", query_type="select", table="users"):
            result = db.query(User).all()
    """

    def __init__(self, operation_name: str, **context):
        self.operation_name = operation_name
        self.context = context
        self.start_time: Optional[float] = None
        self.logger = get_logger("app.performance")

    def __enter__(self):
        self.start_time = time.time()
        self.logger.debug(
            f"Starting {self.operation_name}",
            operation=self.operation_name,
            **self.context,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration_ms = round((time.time() - self.start_time) * 1000, 2)
        else:
            duration_ms = 0

        if exc_type:
            self.logger.error(
                f"Failed {self.operation_name}",
                operation=self.operation_name,
                duration_ms=duration_ms,
                error_type=exc_type.__name__,
                **self.context,
            )
        else:
            log_level = "warning" if duration_ms > 1000 else "info"
            getattr(self.logger, log_level)(
                f"Completed {self.operation_name}",
                operation=self.operation_name,
                duration_ms=duration_ms,
                **self.context,
            )


# ============================================================================
# 🎓 BUSINESS EVENT LOGGING
# ============================================================================


def log_business_event(
    event_name: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    action: Optional[str] = None,
    **additional_context,
) -> None:
    """
    🎓 Log business events with structured data.

    Educational Note:
    Business event logging helps track important operations across your application,
    making it easier to understand user behavior and system performance.

    Usage:
        log_business_event(
            "credit_card_created",
            entity_type="credit_card",
            entity_id=str(credit_card.id),
            action="create",
            account_id=str(account.id),
            amount_limit=1000.00
        )
    """
    logger = get_logger("app.business")
    logger.info(
        f"Business event: {event_name}",
        event_name=event_name,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        **additional_context,
    )


# ============================================================================
# 🎓 SECURITY EVENT LOGGING
# ============================================================================


def log_security_event(
    event_type: str,
    severity: str = "info",
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    **additional_context,
) -> None:
    """
    🎓 Log security-related events.

    Educational Note:
    Security event logging is crucial for auditing, compliance, and detecting
    potential security issues in your application.

    Usage:
        log_security_event(
            "authentication_failed",
            severity="warning",
            user_id="user_123",
            ip_address="192.168.1.100",
            reason="invalid_password",
            attempts=3
        )
    """
    logger = get_logger("app.security")
    getattr(logger, severity)(
        f"Security event: {event_type}",
        event_type=event_type,
        severity=severity,
        user_id=user_id,
        ip_address=ip_address,
        **additional_context,
    )
