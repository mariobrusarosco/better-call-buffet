"""
Error handlers for Better Call Buffet API

This module centralizes all FastAPI error handling to:
- Separate error handling concerns from main app
- Provide consistent error responses across the API
- Enable easy testing of error scenarios
- Foundation for advanced error tracking
"""

import logging

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors (422 status code)

    This provides detailed validation error information while
    logging the errors for debugging purposes.
    """
    logger.error(f"❌ Validation Error: {request.method} {request.url}")
    logger.error(f"💥 Details: {exc.errors()}")

    return JSONResponse(status_code=422, content={"detail": exc.errors()})


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected server errors (500 status code)

    This prevents internal errors from leaking sensitive information
    while ensuring proper logging for debugging.
    """
    logger.error(f"❌ Server Error: {request.method} {request.url}")
    logger.error(f"💥 Exception: {str(exc)}")

    # In production, you might want to hide error details
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle HTTP exceptions (4xx status codes)

    This ensures consistent error response format for HTTP exceptions.
    """
    logger.warning(
        f"⚠️  HTTP {exc.status_code}: {request.method} {request.url} - {exc.detail}"
    )

    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# Future: Advanced error handling features
class ErrorTracker:
    """Foundation for error tracking and monitoring"""

    @staticmethod
    def track_error(error: Exception, context: dict = None) -> None:
        """Track errors for monitoring and alerting (future implementation)"""
        # Future implementation will include:
        # - Integration with Sentry/Rollbar
        # - Error rate monitoring
        # - Alert thresholds
        # - Error categorization
        pass


class ErrorMetrics:
    """Foundation for error metrics collection"""

    @staticmethod
    def increment_error_counter(error_type: str, endpoint: str = None) -> None:
        """Increment error counters for monitoring (future implementation)"""
        # Future implementation will include:
        # - Prometheus/CloudWatch metrics
        # - Error rate by endpoint
        # - Error type distribution
        # - SLA monitoring
        pass
