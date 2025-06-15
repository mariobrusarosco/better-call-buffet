# Better Call Buffet

A modern web application for financial management and analysis.

## Prerequisites

- Python 3.11 or higher
- PostgreSQL (for database)

## Quick Setup

### Windows

```powershell
# Run the setup script
.\setup.ps1

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# Start the application
uvicorn app.main:app --reload
```

### Linux/macOS

```bash
# Make the setup script executable
chmod +x setup.sh

# Run the setup script
./setup.sh

# Activate the virtual environment
source .venv/bin/activate

# Start the application
uvicorn app.main:app --reload
```

## Manual Setup

If you prefer to set up manually or the setup scripts don't work for you:

1. Create a virtual environment:

   ```bash
   python -m venv .venv
   ```

2. Activate the virtual environment:

   - Windows: `.\.venv\Scripts\Activate.ps1`
   - Linux/macOS: `source .venv/bin/activate`

3. Install dependencies:

   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. Install AWS CLI

```bash
curl "https://awscli.amazonaws.com/AWSCLIV2.msi" -o "AWSCLIV2.msi"
```

Add CLI to PATH

```bash
echo 'alias aws="python /c/Users/mario/AppData/Roaming/Python/Python311/Scripts/aws"' >> ~/.bashrc
```

Configure AWS credentials

```bash
aws configure
```

5. Copy the environment template:

   ```bash
   cp .env.example .env
   ```

6. Start the application:
   ```bash
   uvicorn app.main:app --reload
   ```

## Development

- API documentation is available at `http://localhost:8000/docs`
- OpenAPI specification at `http://localhost:8000/openapi.json`

## Project Structure

```
better-call-buffet/
├── app/
│   ├── api/           # API endpoints
│   ├── core/          # Core functionality
│   ├── db/            # Database models and config
│   └── domains/       # Business logic domains
├── docs/              # Documentation
├── scripts/           # Utility scripts
└── tests/             # Test suite
```

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests: `pytest`
4. Format code: `black .`
5. Submit a pull request

## AWS Deployment

### Database Setup (RDS)

1. Create security group for RDS:

```bash
aws ec2 create-security-group \
    --group-name better-call-buffet-db-sg \
    --description "Security group for Better Call Buffet RDS"
```

2. Allow PostgreSQL traffic (development only):

```bash
aws ec2 authorize-security-group-ingress \
    --group-id YOUR_SECURITY_GROUP_ID \
    --protocol tcp \
    --port 5432 \
    --cidr 0.0.0.0/0
```

3. Create RDS instance:

```bash
aws rds create-db-instance \
    --db-instance-identifier better-call-buffet-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 15 \
    --master-username bcb_admin \
    --master-user-password YOUR_PASSWORD \
    --allocated-storage 20 \
    --vpc-security-group-ids YOUR_SECURITY_GROUP_ID \
    --publicly-accessible \
    --db-name better_call_buffet \
    --no-multi-az \
    --storage-type gp2
```

4. Check RDS status:

```bash
aws rds describe-db-instances \
    --db-instance-identifier better-call-buffet-db \
    --query 'DBInstances[0].{Status:DBInstanceStatus,Endpoint:Endpoint.Address}'
```

### Secrets Management

For production deployment, sensitive environment variables are stored in AWS Secrets Manager. Follow these steps to set up:

1. Create the secret in AWS Secrets Manager:

```bash
aws secretsmanager create-secret \
    --name better-call-buffet/production \
    --description "Production environment variables for Better Call Buffet" \
    --secret-string '{"DATABASE_URL":"postgresql://user:pass@host:5432/db","SECRET_KEY":"your-secret-key","ENVIRONMENT":"production","BACKEND_CORS_ORIGINS":["https://yourdomain.com"]}'
```

2. Create IAM policy for accessing secrets:

```bash
aws iam create-policy --policy-name better-call-buffet-secrets-policy --policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"secretsmanager:GetSecretValue\"],\"Resource\":\"arn:aws:secretsmanager:us-east-1:905418297381:secret:better-call-buffet/production-yGOUNN\"}]}"
```

3. Create IAM role for ECS tasks:

```bash
aws iam create-role --role-name better-call-buffet-ecs-role --assume-role-policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"ecs-tasks.amazonaws.com\"},\"Action\":\"sts:AssumeRole\"}]}"
```

4. Attach the secrets policy to the ECS role:

```bash
aws iam attach-role-policy --role-name better-call-buffet-ecs-role --policy-arn arn:aws:iam::905418297381:policy/better-call-buffet-secrets-policy
```

The application will automatically use AWS Secrets Manager when the `ENVIRONMENT` variable is set to `production`. In development, it will continue to use the local `.env` file.

### Container Registry Setup (ECR)

1. Create ECR repository:

```bash
aws ecr create-repository \
    --repository-name better-call-buffet \
    --image-scanning-configuration scanOnPush=true \
    --region us-east-1
```

2. Get AWS account ID:

```bash
aws sts get-caller-identity --query Account --output text
# This will output your AWS account ID, for example: 905418297381
```

3. Authenticate Docker with ECR:

```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 905418297381.dkr.ecr.us-east-1.amazonaws.com
```

4. Build and push Docker image:

```bash
# Build the image
docker build -t better-call-buffet .

# Tag the image for ECR
docker tag better-call-buffet:latest 905418297381.dkr.ecr.us-east-1.amazonaws.com/better-call-buffet:latest

# Push to ECR
docker push 905418297381.dkr.ecr.us-east-1.amazonaws.com/better-call-buffet:latest
```

Notes:

- Replace `905418297381` with your actual AWS account ID
- The repository supports image scanning on push for security
- Images are encrypted at rest using AES-256
- Authentication tokens are valid for 12 hours

## Architecture

```
┌─────────────────────────────────────┐
│  🌐 ROUTER LAYER (HTTP Concerns)     │
│  - Request/Response formatting       │
│  - HTTP status codes                 │
│  - Pydantic validation               │
│  - API versioning                    │
└─────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────┐
│  💼 SERVICE LAYER (Business Logic)   │
│  - Domain operations                 │
│  - Business rules                    │
│  - Data validation                   │
│  - Returns domain models             │
└─────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────┐
│  🗄️ DATA LAYER (Persistence)        │
│  - Database queries                  │
│  - SQLAlchemy models                 │
│  - Transaction management            │
└─────────────────────────────────────┘
```

## License

[License details here]
