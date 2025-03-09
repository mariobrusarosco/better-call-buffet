# Better Call Buffet - Finance Web App

A modern web application for financial management and analysis, built with Domain-Driven Design principles.

## Quick Start with Docker

The easiest way to get started is using Docker:

```bash
# Build and start the application
docker-compose up --build

# The API will be available at:
# - http://localhost:8000
# - http://localhost:8000/docs (Swagger UI)
# - http://localhost:8000/redoc (ReDoc)
```

## Manual Setup

### Prerequisites

- Python 3.8.1+
- Poetry (Python dependency management)
- PostgreSQL (will be needed later)

### Installation

1. Install Poetry (if not already installed):

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

2. Install dependencies:

```bash
poetry install
```

3. Activate the virtual environment:

```bash
poetry shell
```

4. Create a `.env` file in the root directory with your configuration:

```bash
cp .env.example .env
```

5. Run the development server:

```bash
poetry run uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`
API documentation will be available at `http://localhost:8000/docs`

## Development

### Using Docker for Development

1. Start the services:

```bash
docker-compose up
```

2. The application will automatically reload when you make changes to the code.

3. Access PostgreSQL:

There are several ways to access the database:

```bash
# Option 1: Using Docker's psql (Recommended, no local installation needed)
docker-compose exec db psql -U postgres -d better_call_buffet

# Option 2: Using database GUI tools
# Connect using these credentials:
Host: localhost
Port: 5432
User: postgres
Password: postgres
Database: better_call_buffet

# Option 3: If you have psql installed locally (optional)
psql -h localhost -U postgres -d better_call_buffet
```

Note: You don't need PostgreSQL installed on your machine. Docker handles everything!

### Understanding Docker Port Mapping

```
                                        Docker Environment
┌──────────────────┐         ┌───────────────────────────────────────┐
│                  │         │                                       │
│   Your Machine   │         │  ┌─────────────────┐                  │
│   (Host)         │         │  │                 │                  │
│                  │         │  │  PostgreSQL     │                  │
│  localhost:5432 ─┼─────────┼──► Container       │                  │
│                  │         │  │  Port 5432      │                  │
│                  │         │  │                 │                  │
│                  │         │  └─────────────────┘                  │
│                  │         │                                       │
└──────────────────┘         └───────────────────────────────────────┘

Port Mapping:"5432:5432" in docker-compose.yml
             │      │
             │      └─── Container Port
             └────────── Host Port
```

#### How Port Mapping Works

1. **Container Port (Right side)**

   - PostgreSQL runs on port 5432 inside the container
   - This is isolated from your machine by default

2. **Host Port (Left side)**

   - Docker maps the container port to port 5432 on your machine
   - This makes the database accessible via `localhost`

3. **Connection Methods**

   ```
   Method 1 (Direct to Container):
   docker-compose exec db psql ...
   │              │    └─── PostgreSQL command
   │              └────────── Container name
   └─────────────────────────── Docker command

   Method 2 (Through Port Mapping):
   psql -h localhost ...
   │    └─── Connects to mapped port
   └────────── Local psql client
   ```

4. **Why Both Methods Work**
   - Direct container access (Method 1) goes straight to PostgreSQL
   - Port mapping (Method 2) lets local tools connect through `localhost`
   - Same database, different paths to reach it

This is why you can use:

- Local `psql` client
- GUI database tools
- Any application that supports PostgreSQL connections

Choose the method that works best for your workflow!

### Code Style

This project uses:

- Black for code formatting
- Flake8 for style guide enforcement
- isort for import sorting
- mypy for static type checking

Run formatters:

```bash
poetry run black .
poetry run isort .
```

Run linters:

```bash
poetry run flake8
poetry run mypy .
```

## CI/CD

This project uses GitHub Actions for continuous integration and deployment:

- **CI Pipeline**: Runs on every pull request and push to main

  - Linting (black, flake8, isort)
  - Type checking (mypy)
  - Tests (pytest)

- **CD Pipeline**: Runs on push to main
  - Automated deployment (configuration pending)

## Project Structure

The project follows Domain-Driven Design principles, organizing code around business domains rather than technical layers.

```
app/
├── api/
│   └── v1/
│       └── api.py           # API router configuration
├── core/
│   └── config.py           # Core configuration
├── db/
│   └── base.py            # Database configuration
├── domains/               # Business domains
│   ├── users/            # User domain
│   │   ├── models.py     # Database models
│   │   ├── schemas.py    # Pydantic models for API
│   │   ├── service.py    # Business logic
│   │   └── router.py     # API endpoints
│   ├── portfolio/        # Portfolio management
│   ├── transactions/     # Transaction tracking
│   ├── analysis/         # Financial analysis
│   └── market/          # Market data
└── main.py              # Application entry point
```

### Domain Structure

Each domain follows a consistent structure:

- `models.py`: Database models using SQLAlchemy
- `schemas.py`: Pydantic models for request/response validation
- `service.py`: Business logic and domain operations
- `router.py`: FastAPI routes and endpoints

## Development

### Code Style

This project uses:

- Black for code formatting
- Flake8 for style guide enforcement
- isort for import sorting
- mypy for static type checking

Run formatters:

```bash
poetry run black .
poetry run isort .
```

Run linters:

```bash
poetry run flake8
poetry run mypy .
```

## API Endpoints

### Users Domain

- `POST /api/v1/users/`: Create new user
- `GET /api/v1/users/me`: Get current user (requires authentication)

### Health Check

- `GET /health`: API health status
- `GET /`: Welcome message and API information

## Features

### Implemented:

- Basic project structure with DDD
- User domain foundation
- Health check endpoints
- Configuration management
- Database setup

### Coming Soon:

- User Authentication
- Portfolio Management
- Financial Analysis
- Transaction Tracking
- Investment Recommendations

## Domain-Driven Design Benefits

1. **Business-Centric**: Code organization mirrors business concepts
2. **Maintainable**: Clear boundaries between different domains
3. **Scalable**: Easy to add new features within domains
4. **Testable**: Domain isolation makes testing easier
5. **Understandable**: Clear separation of concerns

## Contributing

1. Create a new branch for your feature
2. Follow the domain structure for new features
3. Ensure all tests pass
4. Submit a pull request

## Environment Variables

Required environment variables in `.env`:

```env
# API Settings
API_V1_PREFIX=/api/v1
PROJECT_NAME="Better Call Buffet"
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]

# Security
SECRET_KEY="your-super-secret-key-change-this-in-production"
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/better_call_buffet"
```
