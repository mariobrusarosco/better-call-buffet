# Production-ready FastAPI Dockerfile with Poetry
FROM python:3.11-slim

# Set build arguments for flexibility
ARG POETRY_VERSION=1.7.1

# Create a non-root user for security
RUN groupadd --gid 1000 app && \
    useradd --uid 1000 --gid app --shell /bin/bash --create-home app

# Install system dependencies
# gcc: Needed for compiling Python packages with C extensions
# postgresql-client: For database operations in scripts
# curl: For health checks
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install Poetry with pinned version for reproducibility
RUN pip install --no-cache-dir poetry==$POETRY_VERSION

# Configure Poetry for production
ENV POETRY_NO_INTERACTION=1 \
    POETRY_CACHE_DIR=/tmp/poetry-cache \
    POETRY_HOME="/opt/poetry" \
    POETRY_VENV_IN_PROJECT=1

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app"

# Set working directory
WORKDIR /app

# Copy Poetry configuration files for dependency caching
COPY poetry.lock pyproject.toml ./

# Install dependencies without installing the root package
# This prevents Poetry from trying to install the app as a package
RUN poetry install --without dev --no-root --no-interaction && \
    rm -rf $POETRY_CACHE_DIR

# Copy application code
COPY . .

# Set proper ownership and permissions
RUN chown -R app:app /app && \
    chmod +x /app/scripts/run-prod.sh && \
    chmod +x /app/scripts/run-migrations.sh

# Switch to non-root user for security
USER app

# Expose port (Railway will override with $PORT)
EXPOSE 8000

# Enhanced health check that respects Railway's dynamic port
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Use Poetry to run the application
CMD ["poetry", "run", "/app/scripts/run-prod.sh"]