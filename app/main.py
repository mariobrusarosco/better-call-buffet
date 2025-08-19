import logging

import sentry_sdk
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import api_router
from app.core.config import settings
from app.core.error_handlers import (
    AppException,
    app_exception_handler,
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.core.logging_config import setup_logging
from app.core.middleware import (
    PerformanceMonitoringMiddleware,
    RequestLoggingMiddleware,
)

# Import model registration to register all models
from app.db import model_registration

# Initialize Sentry for error logging (production only)
if settings.SENTRY_DSN and settings.is_production:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        # Only capture errors - no performance monitoring
        traces_sample_rate=0.0,
        # Capture only errors and exceptions
        send_default_pii=False,
        attach_stacktrace=True,
        # Set release version if you want to track deployments
        # release="better-call-buffet@1.0.0",
    )

app = FastAPI(title="Better Call Buffet API")

# Setup structured logging
setup_logging(environment=settings.ENVIRONMENT, log_level="INFO")

# Register error handlers
app.add_exception_handler(AppException, app_exception_handler)  # type: ignore
app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore
app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore
app.add_exception_handler(Exception, general_exception_handler)

# Register logging middleware for per-request logging
# Note: Performance logging can be controlled via ENABLE_PERFORMANCE_LOGGING environment variable
app.add_middleware(
    RequestLoggingMiddleware,
    log_headers=True,
    log_bodies=False,
    enable_performance_logging=settings.ENABLE_PERFORMANCE_LOGGING,  # 🎛️ Controlled via environment
)
app.add_middleware(PerformanceMonitoringMiddleware, slow_request_threshold=1.0)

# Configure CORS
if settings.is_development:
    # In development, allow all origins for easier frontend development
    origins = ["*"]
else:
    # In production, use specific origins
    origins = [str(origin) for origin in settings.BACKEND_CORS_ORIGINS]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)

logger = logging.getLogger("uvicorn.error")


@app.get("/")
async def root():
    return {"message": "Better Call Buffet API!"}


@app.get("/health")
async def health_check():
    return {"status": "healthy api"}


@app.get("/sentry-test")
async def sentry_test():
    """Test endpoint to verify Sentry error logging (production only)."""
    if not settings.is_production:
        return {"message": "Sentry test only available in production"}
    
    # This will trigger a Sentry error report
    raise Exception("Test error for Sentry logging verification")
