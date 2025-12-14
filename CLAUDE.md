# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Tech Stack & Core Dependencies

**Backend Framework:** FastAPI with Python 3.11+
**Database:** PostgreSQL with SQLAlchemy ORM
**Dependency Management:** Poetry
**Database Migrations:** Alembic
**Deployment:** Docker + Railway (serverless)
**Testing:** pytest
**Code Quality:** black (formatting), isort, mypy (type checking), flake8 (linting)
**Monitoring:** Sentry, structured logging with structlog
**Production Server:** Hypercorn

## Essential Development Commands

### Local Development (Docker-based - REQUIRED)

```bash
# Start API and database with hot reload
docker compose up

# Stop services
docker compose down

# Run inside containers (exec commands)
docker compose exec web poetry run <command>

# Run single test file
docker compose exec web poetry run pytest tests/specific_test.py

# Run tests with verbose output
docker compose exec web poetry run pytest -v

# Run tests for specific domain
docker compose exec web poetry run pytest tests/domains/accounts/
```

### Database Operations

```bash
# Apply migrations
docker compose exec web alembic upgrade head

# Create new migration (after model changes)
docker compose exec web alembic revision --autogenerate -m "Description"

# Check current migration status
docker compose exec web alembic current

```

### Code Quality & Testing (ALWAYS run before commits)

```bash
# Format code
docker compose exec web poetry run black .

# Run all tests
docker compose exec web poetry run pytest

# Type checking
docker compose exec web poetry run mypy app

# Linting
docker compose exec web poetry run flake8

# Import sorting
docker compose exec web poetry run isort .

# Security scanning
docker compose exec web poetry run safety check
docker compose exec web poetry run pip-audit
```

### Production & Deployment Scripts

```bash
# Database seeding
docker compose exec web python scripts/seed_db.py
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

## Layers

- Service layer returns models (database objects)
- Router layer returns schemas (API contracts)

## Key Configuration Files

- `pyproject.toml` - Poetry dependencies and tool configurations
- `docker-compose.yml` - Local development environment
- `Dockerfile` - Production container build
- `railway.toml` - Railway deployment configuration
- `alembic.ini` - Database migration settings
- `app/core/config.py` - Application settings via Pydantic

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

## Development Guidelines & Project Standards

### Documentation Standards

1. **ADRs**: Create architectural decision records in `docs/decisions/` for key technology decisions
2. **Fix Logging**: Document issue resolution in `docs/fixing-log/` when prompted with "LOG THE FIX"
3. **Phase Planning**: Use `docs/plans/` for project phases with checklists
4. **Developer Guides**: Create technology guides in `docs/guides/`

### Code Standards

1. **File Naming**: Use kebab-case for all file names
2. **Import Types**: Use `import type { ... }` syntax for type-only imports
3. **Git Commands**: Avoid running git commands in automated scripts
4. **Terminal**: Use Git Bash instead of PowerShell when applicable

### Educational Approach

This project emphasizes learning backend development concepts:

- Provide comprehensive explanations for architecture patterns
- Connect implementation to broader backend best practices
- Explain the "why" behind technical decisions
- Include before/after examples for transformations

## Database Schema Management

**Migration Workflow:**

1. Modify SQLAlchemy models in `app/domains/*/models.py`
2. Generate migration: `alembic revision --autogenerate -m "Description"`
3. Review generated migration file in `migrations/versions/`
4. Test locally: `docker compose exec web alembic upgrade head`
5. Push to main branch (triggers two-stage deployment):
   - **GitHub Actions**: Validates migrations (`alembic check`)
   - **Railway**: Applies migrations (`alembic upgrade head`)

**Model Registration:** All models automatically registered via `app/db/model_registration.py`

## Deployment

**Primary Platform:** Railway (Serverless)

- **Local Development:** Docker Compose for consistent development environment
- **Production:** Railway with automatic scaling and zero-downtime deployments
- **Database:** Production PostgreSQL on managed service with auto-generated `DATABASE_URL`
- **Migrations:** Auto-run on deployment via Railway build process
- **Configuration:** `railway.toml` and environment variables
- **Cost:** Usage-based billing with free tier available
- **Server:** Hypercorn for production (Railway recommended)
- **Deployment:** `railway up` or GitHub push to main branch
- **CI/CD:** GitHub Actions + Railway integration with quality gates

## Common Patterns

**Service Layer Pattern:** Business logic separated from HTTP and data concerns
**Repository Pattern:** Database access abstraction
**Dependency Injection:** Services injected into routers
**Pydantic Models:** Separate request/response schemas from database models
**Error Propagation:** Structured error handling with proper HTTP status codes

## Health Checks & Monitoring

- `/health` - Basic API health check
- `/docs` - FastAPI interactive documentation
- Docker health checks configured for both API and database
- Database connection testing in migration scripts
- Sentry integration for error tracking and performance monitoring
- Structured logging with JSON output for production analysis

## Important Concepts to Explain (Educational Triggers)

When working with these concepts, provide detailed educational explanations:

**Architecture Patterns:**

- Repository Pattern, Dependency Injection, CQRS, Event-driven patterns
- Layered architecture, Factory patterns, Strategy patterns

**Database Concepts:**

- N+1 queries, indexing, connection pooling, transactions
- Caching strategies, migrations, query optimization

**API Design:**

- REST principles, pagination, rate limiting, versioning
- HTTP status codes, content negotiation, API documentation

**Error Handling & Observability:**

- Custom exceptions, structured logging, circuit breakers
- Health checks, graceful degradation, monitoring strategies

**Security & Performance:**

- Authentication vs authorization, input validation, CORS
- Async processing, caching strategies, scaling approaches

## Environment Configuration

**Required Variables:**

- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - Application secret key
- `BACKEND_CORS_ORIGINS` - Allowed CORS origins (JSON array)

**Optional Variables:**

- `ENVIRONMENT` - deployment environment (development/production)
- `ENABLE_PERFORMANCE_LOGGING` - Enable detailed performance logs
- `SENTRY_DSN` - Error tracking and performance monitoring
- `PORT` - Server port (auto-set by deployment platforms)
