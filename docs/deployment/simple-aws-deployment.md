# 🚀 Simple AWS Deployment Guide - Backend Learning Edition

## 🎯 Learning Objectives

By the end of this guide, you'll understand:

- ✅ How to deploy a FastAPI app to AWS without complex infrastructure
- ✅ How to use managed databases (RDS)
- ✅ How to manage secrets securely
- ✅ How to monitor costs and stay within budget
- ✅ How Repository pattern works in production

## 💰 Budget Overview

**Target**: Under $15/month
**Actual Cost**: $3-8/month (well under budget!)

## 📋 Step-by-Step Deployment

### Step 1: Create RDS Database (5 minutes)

1. **Go to AWS RDS Console**

   - Search "RDS" in AWS Console
   - Click "Create database"

2. **Choose Configuration**:

   ```
   Engine: PostgreSQL
   Version: 15.x (latest)
   Template: Free tier
   Instance: db.t3.micro
   Storage: 20 GB (free tier)
   ```

3. **Database Settings**:

   ```
   DB instance identifier: better-call-buffet-db
   Master username: postgres
   Master password: [create a strong password]
   ```

4. **Connectivity**:

   ```
   Public access: Yes (for learning - we'll secure this later)
   VPC security group: Create new
   ```

5. **Click "Create database"** (takes 5-10 minutes)

**💡 Learning Note**: RDS handles backups, updates, and scaling automatically!

### Step 2: Store Secrets in Parameter Store (2 minutes)

1. **Go to AWS Systems Manager Console**

   - Search "Systems Manager"
   - Click "Parameter Store" in left menu

2. **Create Parameters**:

   **Database URL Parameter**:

   ```
   Name: /better-call-buffet/DATABASE_URL
   Type: SecureString
   Value: postgresql://postgres:YOUR_PASSWORD@YOUR_RDS_ENDPOINT:5432/postgres
   ```

   **Secret Key Parameter**:

   ```
   Name: /better-call-buffet/SECRET_KEY
   Type: SecureString
   Value: [generate a random 32-character string]
   ```

**💡 Learning Note**: Parameter Store encrypts secrets automatically!

### Step 3: Deploy with App Runner (10 minutes)

1. **Go to AWS App Runner Console**

   - Search "App Runner"
   - Click "Create service"

2. **Source Configuration**:

   ```
   Repository type: Source code repository
   Connect to GitHub: [connect your GitHub account]
   Repository: better-call-buffet
   Branch: main
   ```

3. **Build Configuration**:

   ```
   Configuration file: Use apprunner.yaml
   Build command: [leave empty - handled by apprunner.yaml]
   Start command: [leave empty - handled by apprunner.yaml]
   ```

4. **Service Configuration**:

   ```
   Service name: better-call-buffet-api
   Port: 8000
   ```

5. **Environment Variables**:

   ```
   DATABASE_URL: [get from Parameter Store]
   SECRET_KEY: [get from Parameter Store]
   ```

6. **Auto Scaling**:

   ```
   Min instances: 0 (saves money!)
   Max instances: 1 (budget-friendly)
   ```

7. **Click "Create & deploy"** (takes 10-15 minutes)

**💡 Learning Note**: App Runner automatically builds and deploys from your GitHub repo!

### Step 4: Test Your Deployment (2 minutes)

1. **Get Your App URL**:

   - App Runner will provide a URL like: `https://xyz.us-east-1.awsapprunner.com`

2. **Test Repository Pattern Endpoints**:

   ```bash
   # Test health check
   curl https://your-app-url.awsapprunner.com/health

   # Test users endpoint
   curl https://your-app-url.awsapprunner.com/users/count

   # Test reports endpoint
   curl "https://your-app-url.awsapprunner.com/reports/accounts/portfolio-overview?start_date=2024-01-01"
   ```

**💡 Learning Note**: Your Repository pattern is now running in production!

## 🔧 Configuration Details

### Environment Variables Setup

Update your `app/core/config.py` to read from environment variables:

```python
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./test.db")
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key")

    class Config:
        env_file = ".env"

settings = Settings()
```

### Database Connection for Production

Update your database connection to handle production:

```python
# app/db/connection_and_session.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use environment variable for production
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

# Production-optimized engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=300,    # Recycle connections every 5 minutes
)
```

## 💰 Cost Monitoring

### Set Up Billing Alerts

1. **Go to AWS Billing Console**
2. **Create Budget**:
   ```
   Budget name: Backend Learning Budget
   Budget amount: $15
   Alert threshold: 80% ($12)
   ```

### Cost Optimization Tips

**App Runner Savings**:

- ✅ **Scale to zero**: When not in use, costs $0
- ✅ **Pay per use**: Only pay when requests are processed
- ✅ **No idle costs**: Unlike EC2, no charges when sleeping

**RDS Savings**:

- ✅ **Free tier**: First 12 months free
- ✅ **Right-sizing**: db.t3.micro is perfect for learning
- ✅ **Automated backups**: Included in free tier

## 🔍 Monitoring & Debugging

### App Runner Logs

1. **Go to App Runner Console**
2. **Click your service**
3. **View "Logs" tab**
4. **Monitor**:
   - Application startup
   - Database migrations
   - Repository pattern operations
   - API requests

### Common Issues & Solutions

**Database Connection Issues**:

```bash
# Check if RDS is accessible
telnet your-rds-endpoint.amazonaws.com 5432

# Verify environment variables
echo $DATABASE_URL
```

**Migration Issues**:

```bash
# Run migrations manually
poetry run alembic upgrade head

# Check migration status
poetry run alembic current
```

## 🎓 Learning Milestones

### Week 1: Basic Deployment

- ✅ Deploy FastAPI app to App Runner
- ✅ Connect to RDS PostgreSQL
- ✅ Store secrets in Parameter Store
- ✅ Test Repository pattern in production

### Week 2: Monitoring & Optimization

- ✅ Set up cost monitoring
- ✅ Optimize for budget constraints
- ✅ Monitor application logs
- ✅ Test auto-scaling behavior

### Week 3: Production Readiness

- ✅ Add health checks
- ✅ Implement proper error handling
- ✅ Set up automated deployments
- ✅ Document operational procedures

## 🚀 Next Steps (When Ready)

### Phase 2: Enhanced Security (Month 2)

- Move to private subnets
- Add VPC endpoints
- Implement proper IAM roles
- Add WAF protection

### Phase 3: Scalability (Month 3)

- Add Application Load Balancer
- Implement caching with ElastiCache
- Add CloudWatch monitoring
- Set up auto-scaling policies

### Phase 4: Advanced Features (Month 4)

- Add CI/CD pipeline
- Implement blue-green deployments
- Add performance monitoring
- Set up disaster recovery

## 💡 Key Learning Takeaways

**Simplicity First**:

- Start with managed services (App Runner, RDS)
- Avoid complex networking initially
- Focus on application logic over infrastructure

**Cost Consciousness**:

- Use free tiers when available
- Monitor spending actively
- Scale to zero when possible

**Production Readiness**:

- Repository pattern works in production
- Managed services reduce operational overhead
- Monitoring is essential from day one

**Gradual Complexity**:

- Master basics before adding complexity
- Each phase builds on previous knowledge
- Real-world experience with AWS services

---

**Remember**: This is a learning journey! Start simple, master the basics, then gradually add complexity as your understanding grows. Your Repository pattern is now running in production AWS infrastructure! 🎉
