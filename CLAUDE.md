# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Tech Stack & Core Dependencies

**Backend Framework:** FastAPI with Python 3.11+
**Database:** PostgreSQL with SQLAlchemy ORM
**Dependency Management:** Poetry
**Database Migrations:** Alembic
**Deployment:** Docker + Fly.io (serverless architecture)
**Testing:** pytest
**Code Quality:** black (formatting), isort, mypy (type checking), flake8 (linting)

## Essential Development Commands

### Local Development (Docker-based)
```bash
# Start API and database with hot reload
docker-compose up

# Stop services
docker-compose down

# Run inside containers (exec commands)
docker-compose exec web poetry run <command>
```

### Database Operations
```bash
# Apply migrations
docker-compose exec web alembic upgrade head

# Create new migration (after model changes)
docker-compose exec web alembic revision --autogenerate -m "Description"

# Check current migration status
docker-compose exec web alembic current

# Alternative: Use migration script
docker-compose exec web ./scripts/run-migrations.sh
```

### Code Quality & Testing
```bash
# Format code
docker-compose exec web poetry run black .

# Run tests
docker-compose exec web poetry run pytest

# Type checking
docker-compose exec web poetry run mypy app

# Linting
docker-compose exec web poetry run flake8

# Import sorting
docker-compose exec web poetry run isort .

# Security scanning
docker-compose exec web poetry run safety check
docker-compose exec web poetry run pip-audit
```

### Production Scripts
```bash
# Production startup (inside container)
./scripts/run-prod.sh

# Migration with connection testing
./scripts/run-migrations.sh
```

## Architecture Overview

**Domain-Driven Design** with clean architecture layers:

```
app/
├── api/v1/                    # API routing layer
├── core/                      # Core configuration, middleware, error handling
├── db/                        # Database connection, model registration, seeds
└── domains/                   # Business domains (see below)
    ├── accounts/
    ├── balance_points/
    ├── brokers/
    ├── credit_cards/
    ├── invoices/
    ├── reports/
    ├── transactions/
    └── users/
```

**Each domain follows a consistent pattern:**
- `models.py` - SQLAlchemy database models
- `schemas.py` - Pydantic request/response models  
- `service.py` - Business logic layer
- `repository.py` - Data access layer
- `router.py` - FastAPI route definitions

**Data Flow:**
1. **Router Layer** - HTTP concerns, validation, status codes
2. **Service Layer** - Business logic, domain operations
3. **Repository Layer** - Database queries, persistence

## Key Configuration Files

- `pyproject.toml` - Poetry dependencies and tool configurations
- `docker-compose.yml` - Local development environment
- `Dockerfile` - Production container build
- `fly.toml` - Fly.io deployment configuration  
- `alembic.ini` - Database migration settings
- `app/core/config.py` - Application settings via Pydantic

## Environment Variables

**Required for local development:**
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - Application secret key
- `BACKEND_CORS_ORIGINS` - Allowed CORS origins (JSON array)

**Optional:**
- `ENVIRONMENT` - deployment environment (development/production)
- `ENABLE_PERFORMANCE_LOGGING` - Enable detailed performance logs

## Error Handling & Logging

**Structured logging** with JSON output configured in `app/core/logging_config.py`

**Custom error handling:**
- `AppException` - Application-specific errors
- Comprehensive error handlers in `app/core/error_handlers.py`
- Request/response logging middleware

## Testing Strategy

**Database Testing:** Tests use separate test database
**Test Structure:** Follow domain structure in tests/
**Running Tests:** Always run via Docker container for consistency

## Development Guidelines

**From Cursor Rules:**
1. **Documentation**: Create ADRs in `docs/decisions/` for architectural decisions
2. **Fix Logging**: Document issue resolution in `docs/fixing-log/`
3. **Phase Planning**: Use `docs/plans/` for project phases
4. **File Naming**: Use kebab-case for file names
5. **Educational Approach**: Provide comprehensive explanations for backend concepts

## Database Schema Management

**Migration Workflow:**
1. Modify SQLAlchemy models in `app/domains/*/models.py`
2. Generate migration: `alembic revision --autogenerate -m "Description"`
3. Review generated migration file in `migrations/versions/`
4. Apply migration: `alembic upgrade head`

**Model Registration:** All models automatically registered via `app/db/model_registration.py`

## Deployment

**Local:** Docker Compose for consistent development environment
**Production:** Fly.io with automatic scaling and zero-downtime deployments
**Database:** Production PostgreSQL on managed service
**Migrations:** Auto-run on deployment via `fly.toml` release command

## Common Patterns

**Service Layer Pattern:** Business logic separated from HTTP and data concerns
**Repository Pattern:** Database access abstraction
**Dependency Injection:** Services injected into routers
**Pydantic Models:** Separate request/response schemas from database models
**Error Propagation:** Structured error handling with proper HTTP status codes

## Health Checks

- `/health` - Basic API health check
- Docker health checks configured for both API and database
- Database connection testing in migration scripts