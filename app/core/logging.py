import logging
import sys

def setup_logging() -> None:
    """Configure logging for the application."""
    # Set base logging level
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            # Console handler
            logging.StreamHandler(sys.stdout),
        ],
    )

def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(name) 