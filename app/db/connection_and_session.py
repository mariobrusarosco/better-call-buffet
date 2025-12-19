from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

# Lazy initialization: delay engine creation until runtime
_engine = None
_SessionLocal = None

def get_engine():
    """
    Get or create database engine (lazy initialization).

    This delays get_settings() call until the function is invoked,
    preventing Settings validation during imports (e.g., in migrations).
    """
    global _engine
    if _engine is None:
        _engine = create_engine(get_settings().DATABASE_URL)
    return _engine


def get_db_session():
    """
    Dependency injection function for FastAPI routes.

    Creates a new database session for each request.
    """
    SessionLocal = get_session_local()  # Get SessionLocal factory lazily
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_session_local():
    """
    Get or create SessionLocal factory (lazy initialization).

    This delays engine creation until the function is invoked.
    """
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal

Base = declarative_base()
