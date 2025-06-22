#!/bin/bash
set -e

echo "🚀 Starting Better Call Buffet API..."

# Check if we should run migrations (only in production/when database is available)
if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
    echo "🔄 Running database migrations..."
    poetry run alembic upgrade head
    echo "✅ Migrations completed!"
fi

# Start the application - try Poetry first, then fallback to global
echo "🌟 Starting FastAPI application..."

# Try poetry run first
if poetry run uvicorn --version > /dev/null 2>&1; then
    echo "Using Poetry uvicorn..."
    exec poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000
else
    echo "Poetry uvicorn not found, using global uvicorn..."
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
fi 