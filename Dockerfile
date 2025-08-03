# Use the Python 3.11 alpine official image
FROM python:3.11-alpine

# Install system dependencies needed for some Python packages
RUN apk add --no-cache gcc musl-dev libffi-dev postgresql-dev curl

# Create and change to the app directory
WORKDIR /app

# Copy requirements and install dependencies first (for better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy local code to the container image
COPY . .

# Run migrations then start the web service
CMD ["sh", "-c", "alembic upgrade head && hypercorn app.main:app --bind ::"]