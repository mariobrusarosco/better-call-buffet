# Use Python 3.11 slim image for smaller size and faster builds
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Install system dependencies including curl for health checks
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy poetry files
COPY pyproject.toml poetry.lock ./

# Install dependencies (--no-root prevents installing the project as a package)
RUN poetry install --only=main --no-root && rm -rf $POETRY_CACHE_DIR

# Copy application code
COPY . .

# Create a startup script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Function to wait for database\n\
wait_for_db() {\n\
    echo "Waiting for database to be ready..."\n\
    until pg_isready -h "${DATABASE_HOST:-localhost}" -p "${DATABASE_PORT:-5432}" -U "${DATABASE_USER:-postgres}" 2>/dev/null; do\n\
        echo "Database is not ready yet. Waiting..."\n\
        sleep 2\n\
    done\n\
    echo "Database is ready!"\n\
}\n\
\n\
# Check if we should run migrations (only in production/when database is available)\n\
if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then\n\
    wait_for_db\n\
    echo "Running database migrations..."\n\
    poetry run alembic upgrade head\n\
    echo "Migrations completed!"\n\
fi\n\
\n\
# Start the application\n\
echo "Starting FastAPI application..."\n\
exec poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000' > /app/start.sh

# Make the startup script executable
RUN chmod +x /app/start.sh

# Expose port (App Runner expects port 8000)
EXPOSE 8000

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use the startup script
CMD ["/app/start.sh"]