from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import Request
import logging

from app.api.v1 import api_router
from app.core.config import settings
from app.core.error_handlers import (
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
# Import model registration to register all models
from app.db import model_registration

app = FastAPI(title="Better Call Buffet API")

# Register error handlers

app.add_exception_handler(Exception, general_exception_handler)

# Register logging middleware for per-request logging

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

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation error for {request.method} {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=400,
        content={"detail": exc.errors()},
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 400:
        logger.error(f"HTTP 400 error for {request.method} {request.url}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.get("/")
async def root():
    return {"message": "Better Call Buffet API!"}


@app.get("/health")
async def health_check():
    return {"status": "healthy api"}
