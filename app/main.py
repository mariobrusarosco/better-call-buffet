from fastapi import FastAPI
import logging

from app.api.v1 import api_router  # Import the api_router

# Simple logging to stdout (CloudWatch will capture this)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Better Call Buffet API")

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