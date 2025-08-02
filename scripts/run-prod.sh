#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

echo "🚀 Starting Better Call Buffet production deployment..."

# Run database migrations first
echo "🔄 Running database migrations..."
if command -v alembic > /dev/null 2>&1; then
    echo "📊 Checking current migration status..."
    alembic current || echo "⚠️  No current migration found"
    
    echo "🔄 Applying migrations..."
    alembic upgrade head
    
    echo "✅ Migrations completed successfully!"
else
    echo "⚠️  Alembic not found, skipping migrations"
fi

# Start the application with Hypercorn (Railway recommended)
echo "🌐 Starting application with Hypercorn..."
exec hypercorn app.main:app --bind "[::]:$PORT"