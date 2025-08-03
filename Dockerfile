# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Generate requirements.txt from Poetry and install with pip
COPY pyproject.toml poetry.lock ./
RUN pip install poetry==1.8.5 && \
    poetry export -f requirements.txt --output requirements.txt --without-hashes --only=main && \
    pip install --no-cache-dir -r requirements.txt && \
    pip uninstall -y poetry

# Copy application code
COPY . .

# Create non-root user for security
RUN adduser --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# Run migrations then start app
CMD ["bash", "-c", "alembic upgrade head && hypercorn app.main:app --bind 0.0.0.0:$PORT"]