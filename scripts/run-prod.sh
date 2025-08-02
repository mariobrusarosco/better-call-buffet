#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Start the application with Hypercorn (Railway recommended)
echo "Starting application with Hypercorn..."
exec hypercorn app.main:app --bind "[::]:$PORT"