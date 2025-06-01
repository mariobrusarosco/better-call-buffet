from fastapi import FastAPI
import logging
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router
from app.core.logging_config import setup_logging

# Setup logging
logger = setup_logging()

from app.api.v1 import api_router  # Import the api_router
from app.db import model_registration  # Import model_registration to register all models

# Simple logging to stdout (CloudWatch will capture this)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Better Call Buffet API")

# Configure CORS
origins = [str(origin) for origin in settings.BACKEND_CORS_ORIGINS]
logger.info(f"Configuring CORS with origins: {origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

@app.get("/")
async def root():
    return {"message": "Better Call Buffet API!"}

@app.get("/health")
async def health_check():
    logger.info("Health check endpoint was called!")
    return {"status": "healthy"}


# Remove or complete this route
# @app.get("/health/live")