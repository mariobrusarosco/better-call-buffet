#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

echo "🔄 Starting database migration process..."

# Check if we can connect to the database
echo "📡 Testing database connection..."
python -c "
import os
from sqlalchemy import create_engine, text
from app.core.config import settings

try:
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text('SELECT version()'))
        version = result.fetchone()[0]
        print(f'✅ Database connection successful: {version[:50]}...')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    exit(1)
"

# Run database migrations
echo "🔄 Running database migrations..."
alembic upgrade head

echo "✅ Database migrations completed successfully!"

# Optional: Show current migration status
echo "📊 Current migration status:"
alembic current 