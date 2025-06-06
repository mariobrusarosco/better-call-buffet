# Environment Variables Guide

This guide explains how to work with environment variables in our project.

## Using Environment Variables in Code

1. **Access Variables Through Settings**
```python
from app.core.config import settings

# Using environment variables
project_name = settings.PROJECT_NAME
api_prefix = settings.API_V1_PREFIX
database_url = settings.DATABASE_URL
```

All environment variables are accessed through the `settings` object, which provides:
- Type checking
- Auto-completion in your IDE
- Default values when applicable

## Adding New Environment Variables

1. **Add to `.env.example`**
```env
# Add your new variable with a example/default value
MY_NEW_VARIABLE="example-value"
```

2. **Add to Settings Class** (in `app/core/config.py`)
```python
class Settings(BaseSettings):
    # Add your new variable with its type
    MY_NEW_VARIABLE: str

    # Or with a default value
    MY_NEW_VARIABLE: str = "default-value"
```

3. **Update Your `.env`**
```env
MY_NEW_VARIABLE="your-actual-value"
```

## Best Practices

1. **Always add new variables to `.env.example`**
   - Helps other developers know what variables are needed
   - Provides documentation for the expected values

2. **Use meaningful names**
   - Use UPPERCASE for variable names
   - Use underscores to separate words
   - Example: `DATABASE_URL`, `API_KEY`, `MAX_CONNECTIONS`

3. **Add comments in `.env.example`**
```env
# Maximum number of database connections (default: 100)
MAX_DB_CONNECTIONS=100
```

4. **Group related variables**
```env
# API Settings
API_KEY=xxx
API_VERSION=v1

# Database Settings
DATABASE_URL=xxx
DATABASE_POOL_SIZE=5
```

## Example Usage

```python
# In your code (e.g., database.py)
from app.core.config import settings

database_config = {
    "url": settings.DATABASE_URL,
    "pool_size": settings.DATABASE_POOL_SIZE,
}

# In config.py
class Settings(BaseSettings):
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 5  # With default value
```

## Common Patterns

1. **Optional Variables**
```python
# In config.py
class Settings(BaseSettings):
    OPTIONAL_VAR: str | None = None
```

2. **Variables with Default Values**
```python
class Settings(BaseSettings):
    TIMEOUT_SECONDS: int = 30
```

3. **Required Variables**
```python
class Settings(BaseSettings):
    REQUIRED_API_KEY: str  # No default value = required
```

## Remember

- Never commit `.env` files to version control
- Always keep `.env.example` updated
- Use meaningful default values in `.env.example`
- Document any special requirements or formats 