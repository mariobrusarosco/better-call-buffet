# Better Call Buffet

## 🚀 Developer Onboarding: The Golden Path for Local Development

Welcome to the Better Call Buffet project! This section will guide you through the ideal developer experience (DX) for starting, developing, and stopping the API—leveraging Docker for consistency, hot reload, and productivity.

### Why Docker?

- **Consistency:** Everyone runs the same environment—no more "works on my machine."
- **Simplicity:** One command starts everything (API + database).
- **Isolation:** No need to install Python, Poetry, or Postgres locally.
- **Production Parity:** Your local setup matches production, reducing surprises.

---

### 🏁 Prerequisites

- **Docker & Docker Compose** must be installed.
  - [Install Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Compose)

---

### ▶️ Quick Start Cheat Sheet

| Action         | Command                                      | What Happens?                   |
| -------------- | -------------------------------------------- | ------------------------------- |
| Start API & DB | `docker-compose up`                          | Hot reload, logs, DB all in one |
| Stop API & DB  | `Ctrl+C` or `docker-compose down`            | Clean shutdown                  |
| Run migrations | `docker-compose exec web alembic ...`        | DB schema updated               |
| Run tests      | `docker-compose exec web poetry run pytest`  | Tests run inside container      |
| Format code    | `docker-compose exec web poetry run black .` | Code formatted inside container |

---

### 🌊 Visual Workflow Diagram

```mermaid
flowchart TD
    A[Edit Code] -- Save --> B[Docker Volume Mount]
    B -- Change Detected --> C[Uvicorn in Docker]
    C -- Hot Reload --> D[API Restarts]
    D -- Logs --> E[Docker Compose Terminal]
    F[Frontend/HTTP Client] -- Request --> D
    D -- Response/Error --> F
```

---

### 🏆 Best Practices

- **Always use Docker Compose** for local development.
- **Never use `--reload` in production** (for security/performance).
- **Check logs** in your terminal for errors and debugging.
- **Use the provided commands** for migrations, testing, and formatting.

---

### 📚 Further Reading

- [App Runner Serverless Architecture Guide](docs/guides/app-runner-serverless-architecture-guide.md)
- [CI/CD Pipeline Guide](docs/guides/cicd-pipeline-guide.md)
- [ADR-005: Smart Branch-Based Docker Build Strategy](docs/decisions/005-smart-branch-based-docker-strategy.md)

---

## The Golden Path: Standardized Development with Docker

To ensure a consistent, predictable, and productive development environment for every engineer, this project uses **Docker as the single, required standard for local development.**

### Why Docker?

- **Consistency:** Eliminates "it works on my machine" problems by ensuring everyone runs the exact same environment, from dependencies to database versions.
- **Simplicity:** Get a fully running application and database with a single command (`docker-compose up`). No need to install and configure PostgreSQL or Python locally.
- **Isolation:** Keeps your local machine clean. All project dependencies are managed inside containers and won't conflict with other projects.
- **Production Parity:** Our local setup mirrors the containerized environment used in production, reducing surprises during deployment.

---

## 🚀 **Serverless Architecture & Enterprise Infrastructure**

### **🎓 Understanding Your Production Setup**

Your Better Call Buffet application runs on **enterprise-grade serverless infrastructure** with automatic load balancing, auto-scaling, and zero-downtime deployments - all without managing any servers!

**📚 [Complete App Runner Serverless Architecture Guide](docs/guides/app-runner-serverless-architecture-guide.md)**

**What you get automatically:**

- ✅ **Auto-scaling containers** (1 to 1000+ users handled seamlessly)
- ✅ **Intelligent load balancing** (requests distributed optimally)
- ✅ **Zero-downtime deployments** (users never see outages)
- ✅ **Enterprise-grade reliability** (automatic failover and recovery)
- ✅ **Cost optimization** (pay only when users access your app)

**Current monthly cost:** ~$3-5 (well under budget, scales with usage)

### **🏗️ Production Architecture**

```mermaid
graph LR
    A[GitHub Push] --> B[CI/CD Pipeline]
    B --> C[AWS App Runner]
    C --> D[Auto-Scaling Containers]
    D --> E[Load Balancer]
    E --> F[Your FastAPI App]
    F --> G[RDS PostgreSQL]
    H[Parameter Store] --> F
```

**Companies using similar architecture:** Netflix, Airbnb, Uber, Stripe

---

## Local Development Setup

### Prerequisites

- **Docker & Docker Compose:** Must be installed on your system.
  - [Install Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)

### Running the Application

1.  **Clone the repository.**
2.  **Navigate to the project root directory.**
3.  **Start the services:**

    ```bash
    docker-compose up -d --build
    ```

That's it. The application stack is now running.

- **API URL:** [http://localhost:8000](http://localhost:8000)
- **Interactive API Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Database:** A PostgreSQL instance is running and exposed on `localhost:5432`. You can connect to it with the credentials in `docker-compose.yml`.

### Stopping the Application

To stop the running containers, execute:

```bash
docker-compose down
```

---

## Common Development Tasks

All commands should be executed from your host machine's terminal in the project root.

### Working with Database Migrations

As you develop new features, you will often need to modify the database schema. This is handled by `Alembic`. Here are the essential commands for your daily work.

**Applying Migrations**

To apply all outstanding migrations and bring the database up to the latest version, run:

```bash
docker-compose exec web alembic upgrade head
```

**Creating a New Migration**

After you have changed your SQLAlchemy models (e.g., in `app/domains/.../models.py`), you need to generate a new migration script. Alembic can often detect these changes automatically.

```bash
docker-compose exec web alembic revision --autogenerate -m "A short, descriptive message about your changes"
```

- `--autogenerate`: Tells Alembic to compare your models to the current database state and generate the migration code.
- `-m "..."`: Provides a message that will become part of the migration file name. Always use a descriptive message!

After running this, a new migration file will appear in the `migrations/versions/` directory. You should always inspect this file to ensure it's correct before committing it.

**Checking the Current Status**

To see the current revision of your database, use:

```bash
docker-compose exec web alembic current
```

This is useful to confirm that your migrations have been applied correctly.

### Running Tests

Execute the `pytest` suite inside the `web` container:

```bash
docker-compose exec web poetry run pytest
```

### Code Formatting & Linting

Run the formatters and linters inside the `web` container:

```bash
# Run Black for formatting
docker-compose exec web poetry run black .
```

---

## Project Structure

```
better-call-buffet/
├── app/
│ ├── api/ # API endpoints
│ ├── core/ # Core functionality
│ ├── db/ # Database models and config
│ └── domains/ # Business logic domains
├── docs/ # Documentation
├── migrations/ # Alembic database migrations
└── docker-compose.yml # Defines the local development environment
```

## Contributing

1. Create a feature branch.
2. Make your changes inside the containerized environment.
3. Run tests: `docker-compose exec web poetry run pytest`
4. Format code: `docker-compose exec web poetry run black .`
5. Submit a pull request.

## CI/CD Pipeline

This project uses an automated CI/CD pipeline powered by GitHub Actions. The pipeline includes:

- **Code Quality Checks**: Automated linting, formatting, and type checking.
- **Security Scanning**: Dependency vulnerability detection.
- **Docker Build**: Containerized application building and testing.
- **Automated Deployment**: Production deployment to AWS.

### 📚 Documentation

- **[CI/CD Pipeline Guide](docs/guides/cicd-pipeline-guide.md)** - Comprehensive guide to our deployment pipeline.
- **[ADR-005: Smart Branch-Based Docker Build Strategy](docs/decisions/005-smart-branch-based-docker-build-strategy.md)** - Cost-optimized CI/CD architecture.
- **[🚀 App Runner Serverless Architecture Guide](docs/guides/app-runner-serverless-architecture-guide.md)** - Deep dive into your enterprise infrastructure.

---

## AWS Deployment

_This section is for reference on how the application is deployed to production infrastructure and is not needed for local development._

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

For production deployment, sensitive environment variables are stored in AWS Secrets Manager.

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

## 📚 Documentation

- **[CI/CD Pipeline Guide](docs/guides/cicd-pipeline-guide.md)** - Comprehensive guide to our deployment pipeline
- **[ADR-005: CI/CD Implementation](docs/decisions/005-cicd-pipeline-implementation.md)** - Architecture decision record

## License

[License details here]
