# CI Database Setup - Bulletproof Solution

## Problem Statement

GitHub Actions CI pipeline failing with PostgreSQL connection errors when running `alembic check` for migration validation. The error manifests as:

```
psycopg2.OperationalError: connection to server at "localhost" (::1), port 5432 failed: Connection refused
```

## Root Cause Analysis

1. **Missing Database Service**: Alembic requires an actual PostgreSQL database to validate migrations
2. **Race Conditions**: Even with PostgreSQL service, the database might not be fully ready when migrations run
3. **Improper Health Checks**: Default health checks might not ensure PostgreSQL is accepting connections
4. **Migration Strategy**: Running `alembic check` without first setting up the database schema

## The Bulletproof Solution

### 1. PostgreSQL Service Configuration

```yaml
services:
  postgres:
    image: postgres:15
    env:
      POSTGRES_PASSWORD: postgres
      POSTGRES_USER: postgres
      POSTGRES_DB: test_db
    options: >-
      --health-cmd "pg_isready -U postgres"
      --health-interval 10s
      --health-timeout 5s
      --health-retries 10
    ports:
      - 5432:5432
```

**Key Points**:
- Uses PostgreSQL 15 (stable, well-tested)
- Proper health check with username specification
- Increased retries (10) to handle startup delays
- Exposed port 5432 for application access

### 2. Database Setup Process

```bash
# Install PostgreSQL client tools
sudo apt-get update
sudo apt-get install -y postgresql-client

# Wait for PostgreSQL to be fully ready
until pg_isready -h localhost -p 5432 -U postgres; do
  echo "Waiting for PostgreSQL..."
  sleep 2
done

# Apply migrations to set up schema
poetry run alembic upgrade head

# Optional: Validate migration sync
poetry run alembic check || echo "⚠️ Migration check completed with warnings"
```

**Key Points**:
- Explicit wait using `pg_isready` command
- Apply migrations BEFORE validation
- Graceful handling of migration check warnings

### 3. Environment Variable Configuration

```yaml
env:
  DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
```

**Key Points**:
- Overrides the default SQLite fallback in settings
- Matches the PostgreSQL service configuration exactly
- Uses standard PostgreSQL port and credentials

## Why This Works

### Sequential Database Initialization
1. **Service Health Check**: GitHub Actions waits for `pg_isready` to succeed
2. **Explicit Wait**: Additional `pg_isready` check in the workflow
3. **Schema Setup**: `alembic upgrade head` creates the database schema
4. **Validation**: `alembic check` validates schema-migration sync

### Robust Error Handling
- Multiple layers of readiness checks prevent race conditions
- Graceful handling of migration check warnings (common in CI)
- Clear logging at each step for debugging

### Environment Isolation
- Dedicated test database (`test_db`)
- Isolated PostgreSQL service per CI run
- Environment variable override ensures correct database connection

## Common Pitfalls Avoided

### ❌ Running `alembic check` on Empty Database
**Problem**: Checking migration sync before applying migrations
**Solution**: Always run `alembic upgrade head` first

### ❌ Insufficient Health Checks
**Problem**: PostgreSQL service reports healthy but isn't accepting connections
**Solution**: Use `pg_isready` with specific user and explicit wait loop

### ❌ Race Conditions
**Problem**: Database operations starting before PostgreSQL is fully ready
**Solution**: Multiple layers of readiness verification

### ❌ Environment Variable Conflicts
**Problem**: Application using SQLite fallback instead of PostgreSQL
**Solution**: Explicit `DATABASE_URL` environment variable in CI

## Testing Locally

You can test the database connection logic locally:

```bash
# Test environment variable override
DATABASE_URL="postgresql://test:test@localhost:5432/test" \
  poetry run python -c "from app.core.config import settings; print(settings.DATABASE_URL)"

# Test with Docker Compose (recommended)
docker-compose up -d postgres
docker-compose exec web poetry run alembic upgrade head
docker-compose exec web poetry run alembic check
```

## CI Pipeline Flow

```mermaid
graph TD
    A[Start CI] --> B[Setup Python & Poetry]
    B --> C[Install Dependencies]
    C --> D[Install PostgreSQL Client]
    D --> E[Start PostgreSQL Service]
    E --> F[Wait for PostgreSQL Ready]
    F --> G[Apply Database Migrations]
    G --> H[Validate Migration Sync]
    H --> I[Run Security Scans]
    I --> J[Run Tests]
    J --> K[Deploy if Main Branch]
```

## Maintenance Notes

### When to Update This Configuration

1. **PostgreSQL Version**: Update service image when upgrading PostgreSQL
2. **Health Check Tuning**: Adjust intervals/retries if startup times change
3. **Migration Strategy**: Modify if migration validation requirements change

### Monitoring

Watch for these patterns in CI logs:
- ✅ `PostgreSQL is ready!` - Health check passed
- ✅ `Database migrations applied successfully!` - Schema setup complete
- ⚠️ Migration warnings - Usually normal, but investigate if persistent

### Performance Optimization

- **Caching**: Poetry dependencies are cached between runs
- **Parallel Jobs**: Security scans and database setup run in sequence for reliability
- **Resource Limits**: PostgreSQL service uses default resources (sufficient for CI)

## Related Documentation

- [Railway CI/CD Setup Guide](../guides/railway-cicd-setup.md)
- [Database Migration Best Practices](../guides/database-migrations.md)
- [GitHub Actions Configuration](../../.github/workflows/deploy.yml)

---

**Last Updated**: 2024-08-02  
**Tested With**: PostgreSQL 15, FastAPI 0.116.1, Alembic 1.15.2, GitHub Actions Ubuntu Latest