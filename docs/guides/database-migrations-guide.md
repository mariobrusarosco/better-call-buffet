# Database Migrations Guide

## Overview
This guide explains how to work with database migrations in Better Call Buffet using Alembic. Migrations allow us to version control our database schema and make changes safely across different environments.

## Prerequisites
- Python 3.8+
- Poetry installed
- Access to project's database
- Environment variables configured (check `.env.example`)

## Initial Setup

1. **Install Dependencies**
   ```bash
   # Alembic is already in our pyproject.toml
   poetry install
   ```

2. **Initialize Alembic** (if not done yet):
   ```bash
   poetry run alembic init migrations
   ```

3. **Configure Environment Variables**
   Create or update your `.env` file with the database connection:
   ```env
   DATABASE_URL=postgresql://user:password@localhost:5432/dbname
   ```

4. **Update migrations/env.py**
   ```python
   import sys
   from pathlib import Path
   sys.path.append(str(Path(__file__).resolve().parents[1]))
   
   from app.db.base import Base
   from app.core.config import settings
   
   # Import all models here
   from app.domains.investments.model import Investment, InvestmentBalancePoint
   from app.domains.accounts.models import Account
   
   # Override sqlalchemy.url with environment variable
   config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
   
   target_metadata = Base.metadata
   ```

5. **Clear sqlalchemy.url in alembic.ini**
   The URL will be set from environment variables, so in `alembic.ini` set:
   ```ini
   sqlalchemy.url = 
   ```

## Working with Migrations

### Creating a New Migration

1. Make changes to your SQLAlchemy models
2. Generate a migration:
   ```bash
   poetry run alembic revision --autogenerate -m "Description of your changes"
   ```
3. The migration will be created in `migrations/versions/`
4. Review the generated migration file to ensure it captures your intended changes

### Applying Migrations

1. Apply all pending migrations:
   ```bash
   poetry run alembic upgrade head
   ```

2. Apply specific number of migrations:
   ```bash
   poetry run alembic upgrade +1  # Apply next migration
   ```

3. Rollback migrations:
   ```bash
   poetry run alembic downgrade -1  # Rollback one migration
   poetry run alembic downgrade base  # Rollback all migrations
   ```

### Best Practices

1. **Always Review Generated Migrations**
   - Alembic's autogenerate is not perfect
   - Check for correct table names, column types, and constraints
   - Ensure foreign keys are properly configured
   - Make sure all models are imported in `env.py`

2. **Test Migrations**
   - Test both upgrade and downgrade operations
   - Use a test database before applying to production
   - Verify data integrity after migration

3. **Naming Conventions**
   - Use descriptive names for migration files
   - Include the purpose of the migration in the message
   - Example: "add_investment_balance_points_table"

4. **Version Control**
   - Always commit migration files to version control
   - Include both the migration script and any related model changes in the same commit

## Common Issues and Solutions

### Migration Not Detecting Changes
- Ensure your models are imported in `env.py`
- Check that your model inherits from `Base`
- Verify the model is properly defined with SQLAlchemy syntax
- Make sure your database URL is correct in `.env`

### Failed Migrations
1. Don't panic! Migrations are transactional
2. Check the error message
3. Common issues:
   - Database connection issues (check `.env` settings)
   - Missing model imports in `env.py`
   - Conflicts with existing tables
4. Rollback using `poetry run alembic downgrade -1`
5. Fix the issue and regenerate the migration

### Database URL Issues
1. Check your `.env` file has the correct DATABASE_URL format:
   ```
   DATABASE_URL=postgresql://username:password@localhost:5432/dbname
   ```
2. Ensure the database exists and is accessible
3. Test the connection using psql or another database client
4. Check if the database user has the right permissions

## Example: Adding a New Table

1. Create your SQLAlchemy model:
```python
class InvestmentBalancePoint(Base):
    __tablename__ = "investment_balance_points"
    id = Column(Integer, primary_key=True)
    investment_id = Column(Integer, ForeignKey("investments.id"))
    balance = Column(Float, nullable=False)
```

2. Import the model in `migrations/env.py`:
```python
from app.domains.investments.model import InvestmentBalancePoint
```

3. Generate migration:
```bash
poetry run alembic revision --autogenerate -m "Add investment balance points table"
```

4. Review and apply:
```bash
poetry run alembic upgrade head
```

## Need Help?
- Check Alembic documentation: https://alembic.sqlalchemy.org/
- Review existing migrations in `migrations/versions/`
- Consult with the team lead for complex schema changes
- Check the project's `.env.example` for required environment variables 