from datetime import datetime
from app.db.base import SessionLocal
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sys
import os
import platform

from app.core.config import settings
from app.api.v1.api import api_router
from app.core.logging_config import setup_logging

# Setup logging
logger = setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json"
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

@app.get("/")
async def root():
    return {
        "message": "Welcome to Better Call Buffet API",
        "docs_url": "/docs",
        "openapi_url": f"{settings.API_V1_PREFIX}/openapi.json"
    }

@app.get("/health")
async def health_check():
    # Set default status code
    status_code = 200
    
    # Check database connection
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
        status_code = 503  # Service Unavailable
    finally:
        if 'db' in locals():
            db.close()

    # Get environment information
    environment_info = {
        "python_version": sys.version,
        "environment": settings.ENVIRONMENT,
        "hostname": platform.node(),
        "system": platform.system(),
        "platform_release": platform.release(),
    }
    
    # Get application information
    app_info = {
        "app_name": settings.PROJECT_NAME,
        "version": "1.0.0",  # This could be read from a version file
        "api_prefix": settings.API_V1_PREFIX,
    }
    
    response_data = {
        "status": "healthy" if status_code == 200 else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "database": db_status,
            "api": "healthy"
        },
        "environment": environment_info,
        "application": app_info
    }
    
    return JSONResponse(content=response_data, status_code=status_code)