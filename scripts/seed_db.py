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
from app.db.base import Base
from app.domains.accounts.models import Account, AccountType
from app.domains.investments.models import Investment, InvestmentBalancePoint
from app.domains.users.models import User
from app.domains.broker.model import Broker

def truncate_tables(db):
    """Truncate all tables in the correct order (respecting foreign keys)"""
    print("Truncating all tables...")
    # Order matters due to foreign key constraints
    tables = [
        "investment_balance_points",
        "investments",
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
            logo="https://example.com/xp-logo.png"
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
                description="Retirement investments", 
                type=AccountType.INVESTMENT.value, 
                balance=25000.00, 
                user_id=test_user.id,
                currency="BRL"
            )
        ]
        db.add_all(accounts)
        db.commit()
        
        # Get the investment account for linking investments
        investment_account = next(acc for acc in accounts if acc.type == AccountType.INVESTMENT.value)
        
        # Seed investments
        print("Seeding investments...")
        investments = [
            Investment(
                symbol="TD",
                name="Tesouro Direto",
                description="Brazilian government bonds",
                quantity=100,
                current_price=100.00,
                currency="BRL",
                user_id=test_user.id,
                account_id=investment_account.id,
                broker_id=test_broker.id
            ),
            Investment(
                symbol="PETR4",
                name="Petrobras",
                description="Petrobras stocks",
                quantity=500,
                current_price=10.00,
                currency="BRL",
                user_id=test_user.id,
                account_id=investment_account.id,
                broker_id=test_broker.id
            )
        ]
        db.add_all(investments)
        db.commit()
        
        # Add some balance points for the investments
        print("Seeding investment balance points...")
        balance_points = []
        for investment in investments:
            balance_points.extend([
                InvestmentBalancePoint(
                    investment_id=investment.id,
                    date=datetime(2024, 1, 1),
                    quantity=investment.quantity,
                    price=investment.current_price * 0.98,  # Initial price 2% lower
                    total_value=investment.quantity * investment.current_price * 0.98
                ),
                InvestmentBalancePoint(
                    investment_id=investment.id,
                    date=datetime(2024, 2, 1),
                    quantity=investment.quantity,
                    price=investment.current_price,  # Current price
                    total_value=investment.quantity * investment.current_price
                )
            ])
        db.add_all(balance_points)
        
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