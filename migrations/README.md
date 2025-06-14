# Database Migrations Guide for Better Call Buffet

## Overview

This project uses Alembic for database migrations with SQLAlchemy models. Migrations allow us to version control our database schema and safely make changes across different environments.

## Prerequisites

- Docker and Docker Compose installed
- Project containers running (`docker compose up -d`)

## Common Migration Commands

### 1. Creating a New Migration

When you make changes to SQLAlchemy models (like adding a table or column), create a new migration:

```bash
# From your local machine
docker exec -it better-call-buffet-web-1 poetry run alembic revision --autogenerate -m "Description of your changes"
```

This will:

- Detect changes between your SQLAlchemy models and current database state
- Create a new migration file in `migrations/versions/`
- Name it with a timestamp and your description

### 2. Applying Migrations

To apply pending migrations:

```bash
# From your local machine
docker exec -it better-call-buffet-web-1 poetry run alembic upgrade head
```

To apply specific number of migrations:

```bash
docker exec -it better-call-buffet-web-1 poetry run alembic upgrade +1  # Apply next migration
```

### 3. Rolling Back Migrations

To rollback migrations:

```bash
docker exec -it better-call-buffet-web-1 poetry run alembic downgrade -1  # Rollback one migration
docker exec -it better-call-buffet-web-1 poetry run alembic downgrade base  # Rollback all migrations
```

### 4. Checking Migration Status

To see which migrations have been applied:

```bash
docker exec -it better-call-buffet-web-1 poetry run alembic current  # Show current revision
docker exec -it better-call-buffet-web-1 poetry run alembic history  # Show migration history
```

### 5. Marking Existing Migrations as Applied

If your database tables already exist but Alembic doesn't know about them:

```bash
docker exec -it better-call-buffet-web-1 poetry run alembic stamp head
```

## Best Practices

1. **Always Review Generated Migrations**

   - Alembic's autogenerate is not perfect
   - Check for correct table names, column types, and constraints
   - Ensure foreign keys are properly configured
   - Make sure all models are imported in `migrations/env.py`

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

- Ensure your models are imported in `migrations/env.py`
- Check that your model inherits from `Base`
- Verify the model is properly defined with SQLAlchemy syntax

### Failed Migrations

1. Don't panic! Migrations are transactional
2. Check the error message
3. Common issues:
   - Database connection issues
   - Missing model imports in `env.py`
   - Conflicts with existing tables
4. Rollback using `docker exec -it better-call-buffet-web-1 poetry run alembic downgrade -1`
5. Fix the issue and regenerate the migration

### Tables Already Exist

If you get "relation already exists" errors:

1. This means your database has tables but Alembic doesn't know about them
2. Use `docker exec -it better-call-buffet-web-1 poetry run alembic stamp head` to mark existing migrations as applied
3. Then proceed with creating new migrations

## Example Workflow

1. Make changes to your models:

   ```python
   # app/domains/investments/models.py
   class InvestmentBalancePoint(Base):
       __tablename__ = "investment_balance_points"
       id = Column(Integer, primary_key=True)
       investment_id = Column(Integer, ForeignKey("investments.id"))
       balance = Column(Float, nullable=False)
   ```

2. Generate migration:

   ```bash
   docker exec -it better-call-buffet-web-1 poetry run alembic revision --autogenerate -m "Add investment balance points table"
   ```

3. Review the generated migration in `migrations/versions/`

4. Apply the migration:
   ```bash
   docker exec -it better-call-buffet-web-1 poetry run alembic upgrade head
   ```

## Production Deployments

When deploying to production:

1. Never run `--autogenerate` in production
2. Always backup the database before applying migrations
3. Run migrations during maintenance windows
4. Test migrations in a staging environment first
5. Have a rollback plan ready

## Need Help?

If you encounter issues:

1. Check Alembic logs for detailed error messages
2. Review the migration file in `migrations/versions/`
3. Consult the project's tech lead
4. Reference Alembic documentation: https://alembic.sqlalchemy.org/
