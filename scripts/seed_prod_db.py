import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid

# Add the parent directory to the path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import models
from app.db.connection_and_session import Base
from app.domains.accounts.models import Account, AccountType

def seed_prod_db():
    # Load environment variables if available
    load_dotenv()
    
    # Get database URL from environment or use default production URL
    # WARNING: Replace password and endpoint with actual production values before running
    DATABASE_URL = os.environ.get("PROD_DATABASE_URL", 
                                "postgresql://postgres:<password>@<rds-endpoint>:5432/better_call_buffet")
    
    print(f"Connecting to production database...")
    engine = create_engine(DATABASE_URL)
    
    # Create a session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Seed accounts
        print("Seeding accounts...")
        accounts = [
            Account(
                name="Production Checking", 
                description="Primary checking account", 
                type=AccountType.CHECKING.value, 
                balance=5000.00, 
                user_id=1
            ),
            Account(
                name="Production Savings", 
                description="Emergency fund", 
                type=AccountType.SAVINGS.value, 
                balance=10000.00, 
                user_id=1
            ),
            Account(
                name="Production Credit Card", 
                description="Primary credit card", 
                type=AccountType.CREDIT.value, 
                balance=500.00, 
                user_id=1
            ),
            Account(
                name="Production Investment", 
                description="Investment portfolio", 
                type=AccountType.INVESTMENT.value, 
                balance=25000.00, 
                user_id=1
            )
        ]
        db.add_all(accounts)
        db.commit()
        
        print("Production database seeding complete!")
        
    except Exception as e:
        print(f"Error seeding production database: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    try:
        seed_prod_db()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1) 