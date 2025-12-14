# Use the Python 3.11 alpine official image
FROM python:3.11-alpine

# Install system dependencies needed for some Python packages and Poetry
RUN apk add --no-cache gcc musl-dev libffi-dev postgresql-dev curl

# Install Poetry (match local version)
RUN pip install poetry==2.2.1

# Configure Poetry: don't create virtual env (we're already in a container)
ENV POETRY_VIRTUALENVS_CREATE=false

# Create and change to the app directory
WORKDIR /app

# Copy Poetry config files first (for better layer caching)
COPY pyproject.toml poetry.lock ./

# Install dependencies using Poetry
RUN poetry install --no-root --no-interaction --no-ansi

# Copy local code to the container image
COPY . .

# Run migrations then start the web service
CMD ["sh", "-c", "alembic upgrade head && hypercorn app.main:app --bind ::"]