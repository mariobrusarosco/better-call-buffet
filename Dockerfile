FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        build-essential \
        gcc \
        python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry using pip (more reliable in WSL environments)
RUN pip install poetry==2.1.2

# Set PATH to include Poetry binaries
ENV PATH="${PATH}:/root/.local/bin"

# Copy README.md first (needed for poetry install)
COPY README.md ./

# Copy poetry files
COPY pyproject.toml poetry.lock* ./

# Configure poetry to not create a virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies (skip installing the root project)
RUN poetry install --no-interaction --no-ansi --no-root

# Copy application code
COPY . .

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser

# Give appuser ownership of app directory
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]