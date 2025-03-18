# Environment Variables in Production

## What Are Environment Variables?

**Environment variables** are dynamic values that can affect the way running processes behave on a computer. They are part of the environment in which a process runs and provide a way to influence program behavior without modifying the code.

Think of environment variables as a **configuration layer** that sits between your application code and the environment it runs in, allowing the same code to behave differently depending on where and how it's deployed.

## Why Use Environment Variables?

For backend developers, environment variables solve several critical challenges:

1. **Configuration Management**: Store settings outside of code
2. **Security**: Keep sensitive information like API keys and passwords out of the codebase
3. **Environment-Specific Behavior**: Run the same code differently in development, staging, and production
4. **Deployment Flexibility**: Change application behavior without code changes
5. **Twelve-Factor App Compliance**: Follow industry best practices for configuration
6. **Container Compatibility**: Configure applications in containerized environments

## Environment Variables in Our Project

In the Better Call Buffet project, we used environment variables extensively for configuration:

### Database Connection

```python
# app/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database configuration from environment variables
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "buffet")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
```

### API Configuration

```python
# app/config.py
import os

# API configuration
API_VERSION = os.getenv("API_VERSION", "v1")
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
```

### AWS Resource Integration

```python
# app/services/storage.py
import os
import boto3

# AWS S3 configuration
S3_BUCKET = os.getenv("S3_BUCKET", "better-call-buffet-assets")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

s3_client = boto3.client(
    's3',
    region_name=AWS_REGION,
    # AWS SDK will automatically use AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY from environment
)
```

## Setting Environment Variables in Elastic Beanstalk

For our project, we configured environment variables in Elastic Beanstalk:

### Console Configuration

Through the AWS Console:

1. Navigate to the Elastic Beanstalk Console
2. Select your environment
3. Go to Configuration → Software
4. Under "Environment properties", add key-value pairs

### Configuration Files

Using `.ebextensions` configuration files:

```yaml
# .ebextensions/environment.config
option_settings:
  aws:elasticbeanstalk:application:environment:
    DB_HOST: buffet-db.cluster-xyz.us-east-1.rds.amazonaws.com
    API_VERSION: v1
    LOG_LEVEL: INFO
    DEBUG_MODE: False
```

### CLI Configuration

Using the AWS CLI:

```bash
aws elasticbeanstalk update-environment \
  --environment-name better-call-buffet-prod \
  --option-settings \
    Namespace=aws:elasticbeanstalk:application:environment,OptionName=DB_HOST,Value=buffet-db.cluster-xyz.us-east-1.rds.amazonaws.com \
    Namespace=aws:elasticbeanstalk:application:environment,OptionName=LOG_LEVEL,Value=INFO
```

## Best Practices for Environment Variables

### 1. Security First

Keep sensitive values secure:

```python
# WRONG - Hardcoded credentials
api_key = "1234567890abcdef"

# RIGHT - Environment variables
api_key = os.getenv("API_KEY")
```

### 2. Default Values

Provide sensible defaults for non-critical variables:

```python
# With default value
log_level = os.getenv("LOG_LEVEL", "INFO")

# Converted to appropriate type
debug_mode = os.getenv("DEBUG_MODE", "False").lower() == "true"
port = int(os.getenv("PORT", "8000"))
```

### 3. Validation

Validate environment variables at startup:

```python
def validate_env_vars():
    required_vars = ["DB_PASSWORD", "API_KEY", "JWT_SECRET"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Call early in application startup
validate_env_vars()
```

### 4. Documentation

Document all environment variables:

```
# Environment Variables
#
# DB_HOST        - Database hostname (required)
# DB_PORT        - Database port (default: 5432)
# DB_NAME        - Database name (default: buffet)
# DB_USER        - Database username (required)
# DB_PASSWORD    - Database password (required)
# LOG_LEVEL      - Logging level (default: INFO)
# DEBUG_MODE     - Enable debug mode (default: False)
```

### 5. Configuration Grouping

Group related environment variables with prefixes:

```
# Database related
DB_HOST=buffet-db.example.com
DB_PORT=5432
DB_NAME=buffet

# Redis related
REDIS_HOST=buffet-cache.example.com
REDIS_PORT=6379

# AWS related
AWS_REGION=us-east-1
AWS_S3_BUCKET=better-call-buffet-assets
```

## Common Patterns for Environment Variables

### Configuration Files

Using environment variables in configuration files:

```python
# config.py
import os

config = {
    "development": {
        "debug": True,
        "database_uri": "postgresql://dev_user:dev_password@localhost/dev_db"
    },
    "production": {
        "debug": False,
        "database_uri": os.getenv("DATABASE_URI")
    }
}

# Select configuration based on environment
env = os.getenv("ENVIRONMENT", "development")
active_config = config[env]
```

### Secret Management

Using AWS Secrets Manager for sensitive environment variables:

```python
import boto3
import json
import os

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# Load database credentials from Secrets Manager
if os.getenv("ENVIRONMENT") == "production":
    db_secrets = get_secret("better-call-buffet/database")
    db_host = db_secrets["host"]
    db_user = db_secrets["username"]
    db_password = db_secrets["password"]
else:
    # Use local environment variables for development
    db_host = os.getenv("DB_HOST", "localhost")
    db_user = os.getenv("DB_USER", "dev_user")
    db_password = os.getenv("DB_PASSWORD", "dev_password")
```

### Multiple Environment Support

Libraries to simplify environment variable handling:

```python
# Using python-dotenv to load .env files
from dotenv import load_dotenv
import os

# Load environment-specific settings
env = os.getenv("ENVIRONMENT", "development")
load_dotenv(f".env.{env}")

# Now use environment variables normally
database_url = os.getenv("DATABASE_URL")
```

## Environment Variables vs. Other Configuration Methods

### Environment Variables vs. Configuration Files

| Environment Variables | Configuration Files |
|-----------------------|---------------------|
| Simple key-value pairs | Can store complex structures |
| Easy to set in container environments | Need to be included in deployment |
| No file to manage | Can be version controlled |
| Limited in size and complexity | Can handle large configurations |

### Environment Variables vs. Cloud Parameter Store

| Environment Variables | Parameter Store |
|-----------------------|-----------------|
| Simple to implement | More complex setup |
| Stored with the application | Centralized storage |
| No versioning | Tracks version history |
| Limited security features | Enhanced security options |

## Security Considerations

### 1. Never Commit Secrets

Keep environment variables with secrets out of version control:

```gitignore
# .gitignore
.env
.env.*
```

### 2. Encryption at Rest

Ensure sensitive environment variables are encrypted when stored:

```yaml
# AWS Elastic Beanstalk with encryption
resources:
  AWSEBSecretKey:
    Type: AWS::KMS::Key
    Properties:
      Description: Key for encrypting Elastic Beanstalk environment variables
      KeyPolicy:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              AWS: !Sub arn:aws:iam::${AWS::AccountId}:root
            Action: 'kms:*'
            Resource: '*'
```

### 3. Principle of Least Privilege

Only provide access to environment variables to processes that need them:

```yaml
# Docker compose limiting environment variables
version: '3'
services:
  api:
    image: better-call-buffet-api
    environment:
      - DB_HOST=database
      - REDIS_HOST=cache
  worker:
    image: better-call-buffet-worker
    environment:
      - QUEUE_URL=https://sqs.us-east-1.amazonaws.com/queue-name
      # Note: worker doesn't get database credentials
```

### 4. Rotation Policies

Implement policies to regularly rotate sensitive values:

```python
# Check age of credentials and warn if too old
import os
import time
from datetime import datetime

creds_updated_at = os.getenv("CREDENTIALS_UPDATED_AT")
if creds_updated_at:
    last_update = datetime.fromtimestamp(int(creds_updated_at))
    days_since_update = (datetime.now() - last_update).days
    
    if days_since_update > 90:  # 90 days
        print("WARNING: Credentials are more than 90 days old. Please rotate them.")
```

## Common Environment Variable Challenges

### 1. Type Conversion

Environment variables are always strings and need conversion:

```python
# Convert string to int with fallback
port = os.getenv("PORT")
try:
    port = int(port) if port else 8000
except ValueError:
    print(f"Invalid PORT value: {port}. Using default: 8000")
    port = 8000
```

### 2. Structured Data

Working with structured data in environment variables:

```python
# Using JSON for structured data
import os
import json

allowed_origins_json = os.getenv("ALLOWED_ORIGINS", "[]")
try:
    allowed_origins = json.loads(allowed_origins_json)
except json.JSONDecodeError:
    print(f"Invalid ALLOWED_ORIGINS JSON: {allowed_origins_json}. Using empty list.")
    allowed_origins = []
```

### 3. Order of Precedence

Managing multiple sources of configuration:

```python
def get_config_value(key, default=None):
    # Check environment variables first
    value = os.getenv(key)
    if value is not None:
        return value
        
    # Then check configuration file
    if key in config_file:
        return config_file[key]
        
    # Finally use default value
    return default
```

### 4. Local Development

Managing environment variables in local development:

```bash
# dev.sh - Script to run application locally with development environment
export DB_HOST=localhost
export DB_USER=dev_user
export DB_PASSWORD=dev_password
export LOG_LEVEL=DEBUG
export DEBUG_MODE=true

python -m app.main
```

## Tools for Environment Variable Management

### 1. direnv

Automatically load environment variables when entering a directory:

```bash
# .envrc
export DB_HOST=localhost
export LOG_LEVEL=DEBUG
```

### 2. docker-compose

Manage environment variables for containerized applications:

```yaml
# docker-compose.yml
version: '3'
services:
  app:
    build: .
    env_file:
      - .env.development
    environment:
      - PORT=8000
```

### 3. Chamber

Secure environment variable management with AWS Parameter Store:

```bash
# Store a secret
chamber write better-call-buffet DB_PASSWORD 'supersecret'

# Run application with secrets
chamber exec better-call-buffet -- python -m app.main
```

### 4. Kubernetes Secrets

Managing environment variables in Kubernetes:

```yaml
# kubernetes-deployment.yaml
apiVersion: v1
kind: Secret
metadata:
  name: better-call-buffet-secrets
type: Opaque
data:
  DB_PASSWORD: c3VwZXJzZWNyZXQ=  # base64 encoded
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: better-call-buffet
spec:
  template:
    spec:
      containers:
      - name: api
        image: better-call-buffet-api
        env:
          - name: DB_HOST
            value: "buffet-db.example.com"
          - name: DB_PASSWORD
            valueFrom:
              secretKeyRef:
                name: better-call-buffet-secrets
                key: DB_PASSWORD
```

## Conclusion

Environment variables are a critical component of modern application deployment, providing a clean separation between code and configuration. They enable the same application code to run in different environments, keep sensitive information secure, and allow for runtime configuration without code changes.

In the Better Call Buffet project, we extensively used environment variables for database connections, API configuration, and AWS resource integration. By following best practices for environment variable management, we created a secure, flexible, and maintainable application deployment on AWS Elastic Beanstalk.

By understanding and effectively using environment variables, backend developers can build applications that are more secure, easier to configure, and adaptable to different deployment scenarios.

## Further Reading

- [The Twelve-Factor App: Config](https://12factor.net/config)
- [AWS Elastic Beanstalk Environment Variables](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/environments-cfg-softwaresettings.html)
- [OWASP Environment Variable Security](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html#rule-4-use-environment-variables-for-sensitive-information)
- [Python dotenv Documentation](https://github.com/theskumar/python-dotenv) 