import logging

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
