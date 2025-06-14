from fastapi import FastAPI
import logging
import sys
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import api_router

# Configure logging to force ALL output to stdout (uvicorn terminal)
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(name)s: %(message)s',
    stream=sys.stdout,
    force=True  # This forces reconfiguration even if handlers exist
)

# Set important loggers to show warnings and errors
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.orm').setLevel(logging.WARNING)
logging.getLogger('fastapi').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Import model registration to register all models
from app.db import model_registration

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
