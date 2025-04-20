from fastapi import FastAPI
import logging

# Simple logging to stdout (CloudWatch will capture this)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Better Call Buffet API")

@app.get("/")
async def root():
    logger.info("Hello World endpoint was called!")
    return {"message": "Hello World!"}

@app.get("/health")
async def health_check():
    logger.info("Health check endpoint was called!")
    return {"status": "healthy"}