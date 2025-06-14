import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import uuid

from app.domains.users import get_current_user_id

# Add the parent directory to the path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import models
from app.db.connection_and_session import Base
from app.domains.accounts.models import Account, AccountType
from app.domains.users.models import User
from app.domains.brokers.models import Broker

def truncate_tables(db):
    """Truncate all tables in the correct order (respecting foreign keys)"""
    print("Truncating all tables...")
    # Order matters due to foreign key constraints
    tables = [
        "accounts",
        "brokers",
        "users"
    ]
    
    # Disable foreign key checks, truncate tables, then re-enable
    db.execute(text("SET session_replication_role = 'replica';"))
    for table in tables:
        print(f"Truncating {table}...")
        db.execute(text(f"TRUNCATE TABLE {table} CASCADE;"))
    db.execute(text("SET session_replication_role = 'origin';"))
    db.commit()

def init_db():
    # Use Docker database configuration
    DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/better_call_buffet"
    
    print(f"Connecting to database...")
    engine = create_engine(DATABASE_URL)
    
    # Create database tables
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    # Create a session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Truncate all tables first
        truncate_tables(db)
        
        # Create a test user
        print("Creating test user...")
        test_user = User(
            email="test@example.com",
            name="Test User",
            id=get_current_user_id()
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
            user_id=test_user.id
        )
        db.add(test_broker)
        db.commit()
        db.refresh(test_broker)
        
        # Seed accounts
        print("Seeding accounts...")
        accounts = [
            Account(
                name="Checking Account", 
                description="Primary checking account", 
                type=AccountType.CASH.value, 
                balance=5000.00, 
                user_id=test_user.id,
                currency="BRL"
            ),
            Account(
                name="Savings Account", 
                description="Emergency fund", 
                type=AccountType.SAVINGS.value, 
                balance=10000.00, 
                user_id=test_user.id,
                currency="BRL"
            ),
            Account(
                name="Credit Card", 
                description="Primary credit card", 
                type=AccountType.CREDIT.value, 
                balance=500.00, 
                user_id=test_user.id,
                currency="BRL"
            ),
            Account(
                name="Investment Account", 
                description="Investment portfolio", 
                type=AccountType.INVESTMENT.value, 
                balance=25000.00, 
                user_id=test_user.id,
                currency="BRL"
            )
        ]
        db.add_all(accounts)
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