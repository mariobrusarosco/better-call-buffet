# End-to-End Deployment Guide: From Local Docker to Production on AWS

This document summarizes the complete process of setting up the local development environment and deploying the "Better Call Buffet" application to AWS with a full CI/CD pipeline. It serves as a log of our progress and a guide for future engineers.

## Part 1: Standardizing Local Development with Docker

The first phase of our work was to establish a single, reliable way for all engineers to run the project. We chose a "Docker-first" approach to ensure consistency and eliminate environment-related bugs.

### Key Decisions & Actions:

- **Mandate Docker:** All local development must be done via Docker Compose. This decision was made to create a consistent environment for all developers.
- **Update Documentation:** The root `README.md` was completely rewritten to present Docker as the "golden path" for setup, and all manual installation instructions were removed.
- **Remove Legacy Files:** The `requirements.txt` and the local `.env` file were deleted. The `.env` file, in particular, was found to be the root cause of a persistent database connection issue within Docker, as it was overriding the `DATABASE_URL` set in `docker-compose.yml`.
- **Refine the `Dockerfile`:** We iteratively fixed the `Dockerfile` to use a modern `poetry install` workflow, correcting several errors (`--no-dev` vs `--without dev`, and adding `--no-root`) to align with our dependency management strategy.

### Final Local Setup Commands:

1.  **Build and Start Services:**
    ```bash
    docker-compose up -d --build
    ```
2.  **Run Database Migrations:**
    ```bash
    docker-compose exec web alembic upgrade head
    ```
3.  **Run Tests:**
    ```bash
    docker-compose exec web poetry run pytest
    ```

---

## Part 2: Provisioning Production Infrastructure on AWS

This is a **one-time setup** performed from the command line using the AWS CLI. All resources were created in the `us-east-2` region.

_Note: In the commands below, `YOUR_AWS_ACCOUNT_ID`, `YOUR_SECURITY_GROUP_ID`, etc., should be replaced with your actual values._

### Step 1: Create ECR Repository

A private repository to store our production Docker images.

```bash
aws ecr create-repository --repository-name better-call-buffet --image-scanning-configuration scanOnPush=true --region us-east-2
```

### Step 2: Create RDS Database & Security Group

A managed PostgreSQL database for our production data.

**A. Create Security Group:**

```bash
aws ec2 create-security-group --group-name better-call-buffet-db-sg --description "Security group for Better Call Buffet RDS" --region us-east-2
# Note the GroupId from the output for the next commands.
```

**B. Authorize Traffic:**

```bash
aws ec2 authorize-security-group-ingress --group-id YOUR_SECURITY_GROUP_ID --protocol tcp --port 5432 --cidr 0.0.0.0/0 --region us-east-2
```

**C. Create RDS Instance:**

```bash
aws rds create-db-instance --db-instance-identifier better-call-buffet-database --db-instance-class db.t3.micro --engine postgres --engine-version 15 --master-username bcb_admin --master-user-password YOUR_SECURE_PASSWORD --allocated-storage 20 --vpc-security-group-ids YOUR_SECURITY_GROUP_ID --publicly-accessible --db-name better_call_buffet --no-multi-az --storage-type gp2 --region us-east-2
```

### Step 3: Secure Credentials with Secrets Manager

Store the database URL and application secret key.

```bash
aws secretsmanager create-secret \
    --name better-call-buffet/production \
    --description "Production environment variables for Better Call Buffet" \
    --secret-string '{"DATABASE_URL":"postgresql://bcb_admin:YOUR_SECURE_PASSWORD@YOUR_DATABASE_ENDPOINT:5432/better_call_buffet","SECRET_KEY":"A_NEW_RANDOM_SECRET_KEY","ENVIRONMENT":"production"}' \
    --region us-east-2
```

---

## Part 3: CI/CD with GitHub Actions and AWS App Runner

This phase connects our code repository to our AWS infrastructure for automated deployments.

### Step 1: Establish Trust between GitHub and AWS (OIDC)

This is a **one-time setup** for the AWS account to trust GitHub as an identity provider.

**A. Get the OIDC Provider Thumbprint:**
This must be done in real-time to get the current, valid thumbprint, as it can rotate.

```bash
openssl s_client -connect token.actions.githubusercontent.com:443 -servername token.actions.githubusercontent.com -showcerts < /dev/null 2>/dev/null | openssl x509 -in /dev/stdin -sha1 -fingerprint -noout
```

**B. Create the OIDC Provider in AWS:**

```bash
aws iam create-open-id-connect-provider --url https://token.actions.githubusercontent.com --client-id-list sts.amazonaws.com --thumbprint-list YOUR_THUMBPRINT_FROM_ABOVE --region us-east-2
```

### Step 2: Create IAM Roles for CI/CD

We created three distinct roles, following the principle of least privilege.

**A. Role for GitHub Actions (To push to ECR):**
_Allows the GitHub workflow to assume a role in AWS._

```bash
# 1. Create Policy
aws iam create-policy --policy-name GitHubActions-ECR-Policy --policy-document '{"Version":"2012-10-17","Statement":[{"Sid":"AllowPushToECR","Effect":"Allow","Action":["ecr:GetAuthorizationToken","ecr:BatchCheckLayerAvailability","ecr:CompleteLayerUpload","ecr:InitiateLayerUpload","ecr:PutImage","ecr:UploadLayerPart"],"Resource":"*"}]}' --region us-east-2
# 2. Create Role
aws iam create-role --role-name GitHubActions-ECR-Role --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Federated":"arn:aws:iam::YOUR_AWS_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"},"Action":"sts:AssumeRoleWithWebIdentity","Condition":{"StringLike":{"token.actions.githubusercontent.com:sub":"repo:YOUR_GITHUB_USERNAME/YOUR_REPO_NAME:*"}}}]}' --region us-east-2
# 3. Attach Policy
aws iam attach-role-policy --role-name GitHubActions-ECR-Role --policy-arn arn:aws:iam::YOUR_AWS_ACCOUNT_ID:policy/GitHubActions-ECR-Policy --region us-east-2
```

**B. Instance Role for App Runner (To read secrets):**
_Allows the running container task to assume a role. It trusts `tasks.apprunner.amazonaws.com`._

```bash
# 1. Create Policy
aws iam create-policy --policy-name AppRunner-Secrets-Policy --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"secretsmanager:GetSecretValue","Resource":"YOUR_SECRET_ARN"}]}' --region us-east-2
# 2. Create Role
aws iam create-role --role-name AppRunner-Instance-Role --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"tasks.apprunner.amazonaws.com"},"Action":"sts:AssumeRole"}]}' --region us-east-2
# 3. Attach Policy
aws iam attach-role-policy --role-name AppRunner-Instance-Role --policy-arn arn:aws:iam::YOUR_AWS_ACCOUNT_ID:policy/AppRunner-Secrets-Policy --region us-east-2
```

**C. Access Role for App Runner (To pull from ECR):**
_Allows the App Runner service to assume a role. It trusts `apprunner.amazonaws.com`._

```bash
# 1. Create Role
aws iam create-role --role-name AppRunner-Access-Role --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"apprunner.amazonaws.com"},"Action":"sts:AssumeRole"}]}' --region us-east-2
# 2. Attach Policy
aws iam attach-role-policy --role-name AppRunner-Access-Role --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess --region us-east-2
```

### Step 3: Create and Configure the App Runner Service

This brings all the pieces together into a running service.

**A. Create Auto-Scaling Configuration:**

```bash
aws apprunner create-auto-scaling-configuration --auto-scaling-configuration-name bcb-autoscaling --max-concurrency 100 --min-size 1 --max-size 3 --region us-east-2
```

**B. Create the Service:**

```bash
aws apprunner create-service --service-name better-call-buffet --source-configuration '{"ImageRepository":{"ImageIdentifier":"YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com/better-call-buffet:latest","ImageRepositoryType":"ECR","ImageConfiguration":{"Port":"8000","RuntimeEnvironmentVariables":{"ENVIRONMENT":"production"}}},"AuthenticationConfiguration":{"AccessRoleArn":"arn:aws:iam::YOUR_AWS_ACCOUNT_ID:role/AppRunner-Access-Role"},"AutoDeploymentsEnabled":true}' --instance-configuration '{"Cpu":"1 vCPU","Memory":"2 GB","InstanceRoleArn":"arn:aws:iam::YOUR_AWS_ACCOUNT_ID:role/AppRunner-Instance-Role"}' --auto-scaling-configuration-arn YOUR_AUTOSCALING_CONFIG_ARN --health-check-configuration '{"Protocol":"HTTP","Path":"/health"}' --region us-east-2
```

**C. Update the Service (As was needed to fix role issues):**

```bash
aws apprunner update-service --service-arn YOUR_APP_RUNNER_SERVICE_ARN --source-configuration '{"ImageRepository":{"ImageIdentifier":"..."},"AuthenticationConfiguration":{"AccessRoleArn":"..."},"AutoDeploymentsEnabled":true}' --region us-east-2
```

### Step 4: Finalizing the CI/CD Workflow

The final step was to make our deployment process robust by creating a startup script to run database migrations and adding a testing stage to our pipeline.

**A. Startup Script (`scripts/run-prod.sh`):**
This script ensures the database schema is updated before the application starts.

```sh
#!/bin/sh
set -e
echo "Running database migrations..."
alembic upgrade head
echo "Migrations complete."
echo "Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**B. Dockerfile `CMD` Update:**
The `Dockerfile`'s final `CMD` instruction was updated to execute this script.

```dockerfile
CMD ["/app/scripts/run-prod.sh"]
```

**C. GitHub Actions Workflow (`.github/workflows/main.yml`):**
The final workflow file was created with two jobs: `lint-and-test` and `build-and-deploy`, ensuring that deployments only proceed if all quality checks pass. The full content is in the file.
