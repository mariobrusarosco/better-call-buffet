name: Enhanced CI/CD Pipeline - Free Tier Optimized

on:
push:
branches: [main, develop]
pull_request:
branches: [main]

env:
AWS_REGION: us-east-2
ECR_REPOSITORY: better-call-buffet
AWS_ACCOUNT_ID: 895583929848

jobs:

# 🧪 Application Testing

test-application:
name: 🧪 Application Tests
runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Cache Poetry dependencies
        uses: actions/cache@v3
        with:
          path: ~/.cache/pypoetry
          key: poetry-${{ runner.os }}-${{ hashFiles('**/poetry.lock') }}

      - name: Install Poetry
        run: |
          curl -sSL https://install.python-poetry.org | python3 -
          echo "$HOME/.local/bin" >> $GITHUB_PATH

      - name: Install dependencies
        run: poetry install --no-root

      - name: Run Database Migrations
        env:
          DATABASE_URL: postgresql://test_user:test_pass@localhost:5432/test_db
        run: poetry run alembic upgrade head

      - name: 🧪 Run Tests
        env:
          DATABASE_URL: postgresql://test_user:test_pass@localhost:5432/test_db
        run: |
          poetry run pytest -v --tb=short
          echo "## 🧪 Test Results" >> $GITHUB_STEP_SUMMARY
          echo "- ✅ All tests passed" >> $GITHUB_STEP_SUMMARY

# 🐳 Docker Build & Push (Main/Develop only)

docker-build-push:
name: 🐳 Docker Build & Push
runs-on: ubuntu-latest
needs: test-application
if: github.event_name == 'push' && (github.ref == 'refs/heads/main' || github.ref == 'refs/heads/develop')
permissions:
id-token: write
contents: read

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          role-to-assume: arn:aws:iam::${{ env.AWS_ACCOUNT_ID }}:role/GitHubActions-ECR-Role
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ${{ steps.login-ecr.outputs.registry }}/${{ env.ECR_REPOSITORY }}:latest
            ${{ steps.login-ecr.outputs.registry }}/${{ env.ECR_REPOSITORY }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: 📊 Image Summary
        run: |
          echo "## 🐳 Docker Build Summary" >> $GITHUB_STEP_SUMMARY
          echo "- ✅ Image built successfully" >> $GITHUB_STEP_SUMMARY
          echo "- 📦 Registry: ${{ steps.login-ecr.outputs.registry }}" >> $GITHUB_STEP_SUMMARY
          echo "- 🏷️ Tags: latest, ${{ github.sha }}" >> $GITHUB_STEP_SUMMARY

# 🐳 Docker Build Test (Feature branches)

docker-build-test:
name: 🧪 Docker Build Test
runs-on: ubuntu-latest
needs: test-application
if: github.event_name == 'push' && github.ref != 'refs/heads/main' && github.ref != 'refs/heads/develop'

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build Docker image (test only)
        uses: docker/build-push-action@v5
        with:
          context: .
          push: false
          tags: better-call-buffet:test
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Test Docker image
        run: |
          docker run --rm --name test-container -d -p 8000:8000 better-call-buffet:test
          sleep 10
          curl -f http://localhost:8000/health || exit 1
          docker stop test-container

# 🚀 Deploy to Production (Main branch only)

deploy-production:
name: 🚀 Deploy to Production
runs-on: ubuntu-latest
needs: docker-build-push
if: github.ref == 'refs/heads/main'
environment: production
permissions:
id-token: write
contents: read

    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          role-to-assume: arn:aws:iam::${{ env.AWS_ACCOUNT_ID }}:role/GitHubActions-ECR-Role
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1

      - name: 🔄 Run Database Migrations
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        run: |
          echo "🔄 Running database migrations before deployment..."

          # Get DATABASE_URL from AWS Parameter Store (FREE tier service!)
          DATABASE_URL=$(aws ssm get-parameter \
            --name "/better-call-buffet/DATABASE_URL" \
            --region ${{ env.AWS_REGION }} \
            --with-decryption \
            --query 'Parameter.Value' \
            --output text)

          # Run migrations in container
          docker run --rm \
            -e ENVIRONMENT=production \
            -e AWS_DEFAULT_REGION=${{ env.AWS_REGION }} \
            -e DATABASE_URL="$DATABASE_URL" \
            $ECR_REGISTRY/${{ env.ECR_REPOSITORY }}:latest \
            /app/scripts/run-migrations.sh

      - name: 🚀 Deploy to App Runner
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        run: |
          echo "🚀 Deploying to App Runner..."

          aws apprunner update-service \
            --service-arn arn:aws:apprunner:${{ env.AWS_REGION }}:${{ env.AWS_ACCOUNT_ID }}:service/better-call-buffet-prod/e7b15d55a36a45d98c4cb3be9f38a582 \
            --source-configuration "{
              \"ImageRepository\": {
                \"ImageIdentifier\": \"$ECR_REGISTRY/${{ env.ECR_REPOSITORY }}:latest\",
                \"ImageConfiguration\": {
                  \"Port\": \"8000\",
                  \"RuntimeEnvironmentVariables\": {
                    \"ENVIRONMENT\": \"production\"
                  }
                },
                \"ImageRepositoryType\": \"ECR\"
              },
              \"AutoDeploymentsEnabled\": false
            }" \
            --region ${{ env.AWS_REGION }}

      - name: 🔍 Verify Deployment
        run: |
          echo "🔍 Waiting for deployment to complete..."
          sleep 30

          # Get App Runner service URL
          SERVICE_URL=$(aws apprunner describe-service \
            --service-arn arn:aws:apprunner:${{ env.AWS_REGION }}:${{ env.AWS_ACCOUNT_ID }}:service/better-call-buffet-prod/e7b15d55a36a45d98c4cb3be9f38a582 \
            --query 'Service.ServiceUrl' \
            --output text)

          # Health check
          curl -f "https://$SERVICE_URL/health" || exit 1

          echo "## 🚀 Deployment Summary" >> $GITHUB_STEP_SUMMARY
          echo "- ✅ Deployment completed successfully" >> $GITHUB_STEP_SUMMARY
          echo "- 🌐 Service URL: https://$SERVICE_URL" >> $GITHUB_STEP_SUMMARY
          echo "- 📊 Health check: Passed" >> $GITHUB_STEP_SUMMARY

# 📊 Cost Monitoring (Free tier)

cost-monitoring:
name: 📊 Cost Monitoring
runs-on: ubuntu-latest
needs: deploy-production
if: github.ref == 'refs/heads/main'
permissions:
id-token: write
contents: read

    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          role-to-assume: arn:aws:iam::${{ env.AWS_ACCOUNT_ID }}:role/GitHubActions-ECR-Role
          aws-region: ${{ env.AWS_REGION }}

      - name: 📊 Check Free Tier Usage
        run: |
          echo "## 📊 AWS Free Tier Usage" >> $GITHUB_STEP_SUMMARY

          # RDS Free Tier (750 hours/month)
          echo "### 🗄️ RDS Usage" >> $GITHUB_STEP_SUMMARY
          echo "- Free tier: 750 hours/month" >> $GITHUB_STEP_SUMMARY
          echo "- Instance: db.t3.micro" >> $GITHUB_STEP_SUMMARY

          # ECR Free Tier (500MB/month)
          ECR_USAGE=$(aws ecr describe-repository-statistics \
            --repository-name ${{ env.ECR_REPOSITORY }} \
            --query 'repositoryStatistics.repositorySizeInBytes' \
            --output text 2>/dev/null || echo "0")

          ECR_USAGE_MB=$((ECR_USAGE / 1024 / 1024))
          echo "### 🐳 ECR Usage" >> $GITHUB_STEP_SUMMARY
          echo "- Current usage: ${ECR_USAGE_MB}MB / 500MB free" >> $GITHUB_STEP_SUMMARY

          if [ $ECR_USAGE_MB -gt 400 ]; then
            echo "- ⚠️ Warning: Approaching free tier limit" >> $GITHUB_STEP_SUMMARY
          else
            echo "- ✅ Well within free tier limits" >> $GITHUB_STEP_SUMMARY
          fi
