#!/bin/bash
set -e

echo "🚀 Starting Better Call Buffet API..."

# Check if we should run migrations (only in production/when database is available)
if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
    echo "🔄 Running database migrations..."
    alembic upgrade head
    echo "✅ Migrations completed!"
fi

# Start the application
echo "🌟 Starting FastAPI application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 