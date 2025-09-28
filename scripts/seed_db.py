import os
import sys
import uuid
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the parent directory to the path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import models
from app.db.connection_and_session import Base
from app.domains.accounts.models import Account, AccountType
from app.domains.brokers.models import Broker
from app.domains.users.models import User


def truncate_tables(db):
    """Truncate all tables in the correct order (respecting foreign keys)"""
    print("Truncating all tables...")
    # Order matters due to foreign key constraints
    tables = ["accounts", "brokers", "users"]

    # Disable foreign key checks, truncate tables, then re-enable
    db.execute(text("SET session_replication_role = 'replica';"))
    for table in tables:
        print(f"Truncating {table}...")
        db.execute(text(f"TRUNCATE TABLE {table} CASCADE;"))
    db.execute(text("SET session_replication_role = 'origin';"))
    db.commit()


def init_db():
    # Use app configuration
    try:
        from app.core.config import settings
        DATABASE_URL = settings.DATABASE_URL
        print(f"Using app configuration for database connection")
    except ImportError:
        # Fallback to Docker database configuration for local development
        DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/better_call_buffet"
        print(f"Using fallback Docker database configuration")

    print(f"Connecting to database...")
    engine = create_engine(DATABASE_URL)

    # Skip creating tables - they're already created by migrations
    print("Tables already created by migration...")

    # Create a session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Truncate all tables first
        truncate_tables(db)

        # Create a test user
        print("Creating test user...")
        import uuid as uuid_module
        test_user = User(
            email="test@example.com",
            full_name="Test User",
            hashed_password="$2b$12$dummy.hashed.password.for.testing",
            id=uuid_module.UUID(
                "550e8400-e29b-41d4-a716-446655440000"
            ),  # Fixed UUID for testing
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)

        # Create test broker
        print("Creating test broker...")
        test_broker = Broker(
            name="XP Investimentos",
            description="Brazilian investment broker",
            colors=["#FFA500", "#000000"],
            logo="https://example.com/xp-logo.png",
            user_id=test_user.id,
        )
        db.add(test_broker)
        db.commit()
        db.refresh(test_broker)

        # Seed accounts using direct SQL to avoid foreign key validation issues
        print("Seeding accounts...")
        from datetime import datetime
        
        accounts_data = [
            {
                'id': str(uuid_module.uuid4()),
                'name': 'Checking Account',
                'description': 'Primary checking account',
                'type': 'cash',
                'user_id': str(test_user.id),
                'broker_id': str(test_broker.id),
                'currency': 'BRL',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
            },
            {
                'id': str(uuid_module.uuid4()),
                'name': 'Savings Account',
                'description': 'Emergency fund',
                'type': 'savings',
                'user_id': str(test_user.id),
                'broker_id': str(test_broker.id),
                'currency': 'BRL',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
            },
            {
                'id': str(uuid_module.uuid4()),
                'name': 'Credit Account',
                'description': 'Primary credit account',
                'type': 'credit',
                'user_id': str(test_user.id),
                'broker_id': str(test_broker.id),
                'currency': 'BRL',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
            },
            {
                'id': str(uuid_module.uuid4()),
                'name': 'Investment Account',
                'description': 'Investment portfolio',
                'type': 'investment',
                'user_id': str(test_user.id),
                'broker_id': str(test_broker.id),
                'currency': 'BRL',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
            },
        ]
        
        for account_data in accounts_data:
            db.execute(text("""
                INSERT INTO accounts (
                    id, name, description, type, 
                    user_id, broker_id, currency, 
                    is_active, created_at, updated_at
                ) VALUES (
                    :id, :name, :description, :type,
                    :user_id, :broker_id, :currency,
                    true, :created_at, :updated_at
                )
            """), account_data)
        
        db.commit()

        print("Database seeding complete!")

    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    try:
        init_db()
    except Exception as e:
        print(f"Error initializing database: {e}")
        sys.exit(1)
