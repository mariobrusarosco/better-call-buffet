# Database Seeding Guide

This guide explains how to seed data in both development and production environments for the Better Call Buffet application.

## Table of Contents

1. [Overview](#overview)
2. [Development Environment](#development-environment)
3. [Production Environment](#production-environment)
4. [Custom Seeding](#custom-seeding)
5. [Troubleshooting](#troubleshooting)

## Overview

Database seeding is the process of populating a database with initial data. This is useful for:
- Setting up development environments
- Creating test data
- Initializing production systems with required data
- Creating demo accounts or sample data

## Development Environment

### Using the Development Seed Script

1. **Ensure your environment is set up**:
   ```bash
   # Install dependencies
   poetry install

   # Set up your .env file
   cp .env.example .env
   # Edit .env with your local database credentials
   ```

2. **Run the development seed script**:
   ```bash
   poetry run python scripts/seed_db.py
   ```

### Default Development Data

The development seed script creates:
- Test user accounts
- Sample checking and savings accounts
- Demo investment accounts
- Example transactions
- Test broker relationships

## Production Environment

### Important Considerations

Before seeding production:
1. **Backup your database**
2. **Review the seed data** for sensitive information
3. **Test the seeding process** in a staging environment
4. **Ensure proper access controls** are in place

### Production Seeding Methods

#### Method 1: Using the Production Seed Script

```bash
# Connect to the production environment
aws ssm start-session --target <instance-id>

# Navigate to application directory
cd /var/app/current

# Run the production seed script
sudo python scripts/seed_prod_db.py
```

#### Method 2: Using SQL Scripts

1. **Create your seed SQL file**:
   ```sql
   -- seed_prod_db.sql
   BEGIN;
   
   -- Seed users
   INSERT INTO users (id, email, hashed_password, is_active)
   VALUES 
     ('550e8400-e29b-41d4-a716-446655440000', 'admin@example.com', 'hashed_password', true);
   
   -- Seed accounts
   INSERT INTO accounts (name, description, type, balance, user_id)
   VALUES 
     ('Main Checking', 'Primary checking account', 'checking', 1000.00, '550e8400-e29b-41d4-a716-446655440000');
   
   COMMIT;
   ```

2. **Execute the SQL script**:
   ```bash
   psql -h <rds-endpoint> -U postgres -d better_call_buffet -f seed_prod_db.sql
   ```

## Custom Seeding

### Creating Custom Seed Data

1. **Create a new Python script**:
   ```python
   # custom_seed.py
   from app.db.session import SessionLocal
   from app.domains.accounts.models import Account
   from app.domains.users.models import User
   
   def seed_custom_data():
       db = SessionLocal()
       try:
           # Add your custom seeding logic here
           user = User(
               email="custom@example.com",
               hashed_password="your_hashed_password"
           )
           db.add(user)
           db.commit()
           
           account = Account(
               name="Custom Account",
               type="checking",
               balance=1000.00,
               user_id=user.id
           )
           db.add(account)
           db.commit()
           
       except Exception as e:
           print(f"Error seeding custom data: {e}")
           db.rollback()
       finally:
           db.close()
   
   if __name__ == "__main__":
       seed_custom_data()
   ```

2. **Run your custom seed script**:
   ```bash
   poetry run python custom_seed.py
   ```

### Seeding Specific Tables

You can create targeted seed scripts for specific domains:

```python
# seed_investments.py
from app.db.session import SessionLocal
from app.domains.investments.models import Investment, InvestmentBalancePoint

def seed_investments():
    db = SessionLocal()
    try:
        # Add investment data
        investment = Investment(
            name="Tech Growth Fund",
            description="Technology sector growth fund",
            user_id="user_uuid_here"
        )
        db.add(investment)
        db.commit()
        
        # Add balance points
        balance_point = InvestmentBalancePoint(
            investment_id=investment.id,
            balance=10000.00,
            date=datetime.utcnow()
        )
        db.add(balance_point)
        db.commit()
        
    except Exception as e:
        print(f"Error seeding investments: {e}")
        db.rollback()
    finally:
        db.close()
```

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Check your database credentials
   - Verify the database exists
   - Ensure proper network access

2. **Constraint Violations**
   - Check foreign key relationships
   - Verify unique constraints
   - Ensure data types match

3. **Permission Issues**
   - Verify database user permissions
   - Check file system permissions for scripts
   - Ensure proper AWS IAM roles in production

### Verification

After seeding, verify the data:

```sql
-- Check user count
SELECT COUNT(*) FROM users;

-- Verify account balances
SELECT name, balance FROM accounts;

-- Check investment data
SELECT * FROM investments;
```

### Rollback Strategy

If seeding fails:

1. **For development**:
   ```bash
   # Drop and recreate the database
   dropdb better_call_buffet
   createdb better_call_buffet
   
   # Run migrations
   poetry run alembic upgrade head
   
   # Try seeding again
   poetry run python scripts/seed_db.py
   ```

2. **For production**:
   - Restore from the backup taken before seeding
   - Review error logs
   - Fix issues in the seed data
   - Try again with corrected data 