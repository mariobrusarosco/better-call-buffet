#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

echo "🚀 Starting Better Call Buffet production deployment..."

# Ensure we're in the right directory
cd /app

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERROR: DATABASE_URL environment variable is not set"
    exit 1
fi

# Check if PORT is set (Railway should set this automatically)
if [ -z "$PORT" ]; then
    echo "⚠️  WARNING: PORT not set, defaulting to 8000"
    export PORT=8000
fi

# Run database migrations first
echo "🔄 Running database migrations..."
if command -v alembic > /dev/null 2>&1; then
    echo "📊 Checking current migration status..."
    alembic current || echo "⚠️  No current migration found (this is normal for first deployment)"
    
    echo "🔄 Applying migrations..."
    alembic upgrade head
    
    echo "✅ Migrations completed successfully!"
else
    echo "❌ ERROR: Alembic not found, cannot run migrations"
    exit 1
fi

# Start the application with Hypercorn (Railway recommended)
echo "🌐 Starting application with Hypercorn on port $PORT..."
exec hypercorn app.main:app --bind "0.0.0.0:$PORT" --access-logfile - --error-logfile -