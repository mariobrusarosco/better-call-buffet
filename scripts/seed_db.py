import os
import sys
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid

from app.domains.users import get_current_user_id

# Add the parent directory to the path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import models
from app.db.base import Base
from app.domains.accounts.models import Account, AccountType
from app.domains.investments.model import Investment, InvestmentType, InvestmentBalancePoint
from app.domains.users.models import User

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
        
        # Seed investments
        print("Seeding investments...")
        investments = [
            Investment(
                name="Tesouro Direto",
                description="Brazilian government bonds",
                type=InvestmentType.RENDA_FIXA.value,
                amount=10000.00,
                currency="BRL",
                user_id=test_user.id
            ),
            Investment(
                name="PETR4",
                description="Petrobras stocks",
                type=InvestmentType.RENDA_VARIAVEL.value,
                amount=5000.00,
                currency="BRL",
                user_id=test_user.id
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
                    balance=investment.amount,
                    movement=investment.amount
                ),
                InvestmentBalancePoint(
                    investment_id=investment.id,
                    date=datetime(2024, 2, 1),
                    balance=investment.amount * 1.02,  # 2% return
                    movement=None
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