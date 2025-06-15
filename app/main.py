from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import settings
from app.core.error_handlers import (
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.core.logging_config import LoggingConfig

# Configure logging first
LoggingConfig.configure_logging()
logger = LoggingConfig.get_logger(__name__)

# Import model registration to register all models
from app.db import model_registration

app = FastAPI(title="Better Call Buffet API")

# Register error handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Configure CORS
origins = [str(origin) for origin in settings.BACKEND_CORS_ORIGINS]
logger.info(f"🌐 Configuring CORS with origins: {origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)


@app.get("/")
async def root():
    return {"message": "Better Call Buffet API!"}


@app.get("/health")
async def health_check():
    logger.info("💚 Health check endpoint called")
    return {"status": "healthy"}
