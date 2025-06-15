import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine

# Add the parent directory to the path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import models that need to be created
from app.db.connection_and_session import Base
from app.domains.users.models import User


def init_db():
    load_dotenv()
    DATABASE_URL = os.environ.get("DATABASE_URL")

    if not DATABASE_URL:
        print("Error: DATABASE_URL environment variable not set")
        sys.exit(1)

    print(f"Connecting to database...")
    engine = create_engine(DATABASE_URL)

    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)

    print("Database initialization complete!")


if __name__ == "__main__":
    try:
        init_db()
    except Exception as e:
        print(f"Error initializing database: {e}")
        sys.exit(1)
