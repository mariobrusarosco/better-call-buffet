import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the parent directory to the path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import models
from app.db.base import Base
from app.domains.accounts.models import Account, AccountType

def init_db():
    load_dotenv()
    DATABASE_URL = os.environ.get("DATABASE_URL")
    
    if not DATABASE_URL:
        print("Error: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    print(f"Connecting to database...")
    engine = create_engine(DATABASE_URL)
    
    # Create database tables
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    # Create a session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Seed accounts
        print("Seeding accounts...")
        accounts = [
            Account(
                name="Checking Account", 
                description="Primary checking account", 
                type=AccountType.CHECKING.value, 
                balance=5000.00, 
                user_id=1  # Using placeholder ID since users were removed
            ),
            Account(
                name="Savings Account", 
                description="Emergency fund", 
                type=AccountType.SAVINGS.value, 
                balance=10000.00, 
                user_id=1
            ),
            Account(
                name="Credit Card", 
                description="Primary credit card", 
                type=AccountType.CREDIT.value, 
                balance=500.00, 
                user_id=1
            ),
            Account(
                name="Investment Account", 
                description="Retirement investments", 
                type=AccountType.INVESTMENT.value, 
                balance=25000.00, 
                user_id=1
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