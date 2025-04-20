from fastapi import FastAPI
from app.core.logging import setup_logging, get_logger

# Initialize logging
setup_logging()
logger = get_logger(__name__)

app = FastAPI(title="Better Call Buffet API")

@app.get("/")
async def root():
    logger.info("Hello World endpoint was called!")
    return {"message": "Hello World!"}

@app.get("/health")
async def health_check():
    logger.info("Health check endpoint was called!")
    return {"status": "healthy"}