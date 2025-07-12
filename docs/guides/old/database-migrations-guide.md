# Database Migrations Guide

## Overview

This guide explains how to work with database migrations in Better Call Buffet using Alembic. Migrations allow us to version control our database schema and make changes safely across different environments.

## Prerequisites

- Docker and Docker Compose installed
- Project cloned and Docker containers running
- Access to project's database through Docker containers

## Project Setup

Better Call Buffet uses Docker Compose to manage the database and application containers. All migration commands should be run inside the Docker containers to ensure proper environment configuration.

### Starting the Application

1. **Start all services**:

   ```bash
   docker-compose up -d
   ```

2. **Verify containers are running**:

   ```bash
   docker-compose ps
   ```

   You should see containers similar to:

   - `better-call-buffet-web-1` (FastAPI application)
   - `better-call-buffet-db-1` (PostgreSQL database)

3. **Check container names**:
   ```bash
   docker ps
   ```

## Working with Migrations

### Creating a New Migration

1. **Make changes to your SQLAlchemy models** in `app/domains/*/models.py`

2. **Generate a migration using Docker**:

   ```bash
   docker exec better-call-buffet-web-1 poetry run alembic revision --autogenerate -m "Description of your changes"
   ```

3. **The migration will be created** in `migrations/versions/`

4. **Review the generated migration file** to ensure it captures your intended changes

### Applying Migrations

1. **Apply all pending migrations**:

   ```bash
   docker exec better-call-buffet-web-1 poetry run alembic upgrade head
   ```

2. **Apply specific number of migrations**:

   ```bash
   docker exec better-call-buffet-web-1 poetry run alembic upgrade +1  # Apply next migration
   ```

3. **Rollback migrations**:
   ```bash
   docker exec better-call-buffet-web-1 poetry run alembic downgrade -1  # Rollback one migration
   docker exec better-call-buffet-web-1 poetry run alembic downgrade base  # Rollback all migrations
   ```

### Checking Migration Status

1. **Check current migration status**:

   ```bash
   docker exec better-call-buffet-web-1 poetry run alembic current
   ```

2. **See what migrations are available**:

   ```bash
   docker exec better-call-buffet-web-1 poetry run alembic heads
   ```

3. **View migration history**:
   ```bash
   docker exec better-call-buffet-web-1 poetry run alembic history
   ```

### After Git Pull - Applying New Migrations

When you pull changes from the repository that include new migrations, follow these steps:

1. **Ensure containers are running**:

   ```bash
   docker-compose up -d
   ```

2. **Check your current migration status**:

   ```bash
   docker exec better-call-buffet-web-1 poetry run alembic current
   ```

3. **See what migrations are available**:

   ```bash
   docker exec better-call-buffet-web-1 poetry run alembic heads
   ```

4. **Apply all pending migrations**:

   ```bash
   docker exec better-call-buffet-web-1 poetry run alembic upgrade head
   ```

5. **Verify the migration was successful**:
   ```bash
   docker exec better-call-buffet-web-1 poetry run alembic current
   ```

**Quick Command**: If you just want to apply all pending migrations after a git pull:

```bash
docker exec better-call-buffet-web-1 poetry run alembic upgrade head
```

## Environment Configuration

The project uses Docker Compose with environment variables defined in `docker-compose.yml`. The database connection is automatically configured for the containerized environment:

```yaml
environment:
  - DATABASE_URL=${DATABASE_URL:-postgresql://postgres:postgres@db:5432/better_call_buffet}
```

**No manual environment setup required** when using Docker Compose - all environment variables are handled automatically.

## Troubleshooting

### Container Issues

1. **Check if containers are running**:

   ```bash
   docker-compose ps
   ```

2. **If containers are not running, start them**:

   ```bash
   docker-compose up -d
   ```

3. **Check container logs**:

   ```bash
   docker-compose logs web
   docker-compose logs db
   ```

4. **Rebuild containers if needed**:
   ```bash
   docker-compose down
   docker-compose build
   docker-compose up -d
   ```

### Migration Errors

1. **Database connection issues**:

   - Ensure `better-call-buffet-db-1` container is healthy
   - Check database logs: `docker-compose logs db`
   - Verify network connectivity between containers

2. **Container name issues**:

   - Use `docker ps` to get exact container names
   - Container names may vary (e.g., `web-1`, `better-call-buffet-web-1`)

3. **Permission issues**:
   - Ensure Docker has proper permissions
   - Try restarting Docker Desktop if on Windows/Mac

### Alternative Container Names

If `better-call-buffet-web-1` doesn't work, try these alternatives:

```bash
# Using docker-compose exec (if service is 'web')
docker-compose exec web poetry run alembic upgrade head

# Using shorter container name
docker exec web-1 poetry run alembic upgrade head

# Check actual container names
docker ps --format "table {{.Names}}\t{{.Status}}"
```

## Best Practices

1. **Always Use Docker Commands**

   - Never run Alembic commands directly on host machine
   - Always use `docker exec` to run inside containers
   - Ensures consistent environment and database access

2. **Review Generated Migrations**

   - Alembic's autogenerate is not perfect
   - Check for correct table names, column types, and constraints
   - Ensure foreign keys are properly configured
   - Make sure all models are imported in `migrations/env.py`

3. **Test Migrations**

   - Test both upgrade and downgrade operations
   - Use a test database before applying to production
   - Verify data integrity after migration

4. **Naming Conventions**

   - Use descriptive names for migration files
   - Include the purpose of the migration in the message
   - Example: "add_investment_balance_points_table", "make_broker_logo_nullable"

5. **Version Control**
   - Always commit migration files to version control
   - Include both the migration script and any related model changes in the same commit

## Common Migration Scenarios

### Example 1: Making a Field Optional

1. **Update the model**:

   ```python
   # In app/domains/brokers/models.py
   logo = Column(String, nullable=True)  # Changed from nullable=False
   ```

2. **Update Pydantic schemas**:

   ```python
   # In app/domains/brokers/schemas.py
   logo: Optional[str] = None  # Changed from str
   ```

3. **Generate migration**:

   ```bash
   docker exec better-call-buffet-web-1 poetry run alembic revision --autogenerate -m "make_broker_logo_nullable"
   ```

4. **Apply migration**:
   ```bash
   docker exec better-call-buffet-web-1 poetry run alembic upgrade head
   ```

### Example 2: Adding a New Table

1. **Create your SQLAlchemy model**:

   ```python
   class NewTable(Base):
       __tablename__ = "new_table"
       id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
       name = Column(String, nullable=False)
   ```

2. **Import the model in `migrations/env.py`**:

   ```python
   from app.domains.new_domain.models import NewTable
   ```

3. **Generate migration**:

   ```bash
   docker exec better-call-buffet-web-1 poetry run alembic revision --autogenerate -m "add_new_table"
   ```

4. **Review and apply**:
   ```bash
   docker exec better-call-buffet-web-1 poetry run alembic upgrade head
   ```

## Production Considerations

For production deployments, consider:

1. **Backup Database Before Migrations**
2. **Run Migrations During Maintenance Windows**
3. **Test Migrations on Staging Environment First**
4. **Monitor Application Performance After Schema Changes**

## Need Help?

- Check Alembic documentation: https://alembic.sqlalchemy.org/
- Review existing migrations in `migrations/versions/`
- Check Docker Compose logs: `docker-compose logs`
- Consult with the team lead for complex schema changes
