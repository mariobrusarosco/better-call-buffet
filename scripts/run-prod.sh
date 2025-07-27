#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Start the application
echo "Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips '*' 