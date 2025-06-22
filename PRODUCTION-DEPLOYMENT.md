# 🚀 Better Call Buffet - Production Deployment Guide

## Quick Start (15 minutes to production!)

### Step 1: Generate Production Secrets (2 minutes)

```bash
python scripts/setup-production-secrets.py
```

This will output secrets you need to add to GitHub.

### Step 2: Add GitHub Secrets (5 minutes)

1. Go to **GitHub Repository** → **Settings** → **Secrets and variables** → **Actions**
2. Click **"New repository secret"** for each:

```
AWS_ACCESS_KEY_ID=your-aws-access-key-id
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key
AWS_REGION=us-east-1
ECR_REGISTRY=YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
PROD_DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@YOUR_RDS_ENDPOINT:5432/better_call_buffet
PROD_SECRET_KEY=generated-secret-key-from-script
```

**⚠️ Don't have these yet?** See [Getting AWS Credentials](#getting-aws-credentials) below.

### Step 3: Deploy! (8 minutes)

```bash
# Trigger deployment by pushing to main
git add .
git commit -m "🚀 Deploy to production"
git push origin main
```

Watch the deployment at: `https://github.com/YOUR_USERNAME/better-call-buffet/actions`

### Step 4: Get Your Live API URL

After deployment completes:

1. Go to **AWS Console** → **App Runner**
2. Find your service: `better-call-buffet-prod`
3. Copy the **Service URL**
4. Test it: `https://your-service-url.awsapprunner.com/health`

🎉 **Your API is live!**

---

## Getting AWS Credentials

### Option 1: Use Existing AWS Account

If you have AWS CLI configured:

```bash
aws sts get-caller-identity  # Should show your account
```

Your credentials are in: `~/.aws/credentials`

### Option 2: Create New IAM User

1. **AWS Console** → **IAM** → **Users** → **Create user**
2. User name: `better-call-buffet-deploy`
3. **Attach policies**:
   - `AWSElasticBeanstalkFullAccess`
   - `AmazonEC2ContainerRegistryFullAccess`
   - `AppRunnerFullAccess`
   - `AmazonRDSFullAccess`
4. **Create access key** → **Command Line Interface (CLI)**
5. Copy the `Access Key ID` and `Secret Access Key`

---

## Troubleshooting

### ❌ Pipeline Fails on "Push to ECR"

**Problem**: ECR repository doesn't exist

**Solution**:

```bash
aws ecr create-repository --repository-name better-call-buffet --region us-east-1
```

### ❌ Pipeline Fails on "Deploy to App Runner"

**Problem**: Invalid service ARN

**Solution**: Remove `APP_RUNNER_SERVICE_ARN` secret temporarily. The pipeline will create the service.

### ❌ App Won't Start

**Problem**: Database connection issues

**Solution**:

1. Check your `PROD_DATABASE_URL` format
2. Verify your RDS instance is running
3. Check security groups allow port 5432

### ❌ Database Migrations Fail

**Problem**: Tables don't exist

**Solution**:

```bash
# Connect to your RDS and run:
psql -h YOUR_RDS_ENDPOINT -U postgres -d better_call_buffet

# Check if tables exist:
\dt

# If no tables, check migration logs in App Runner
```

---

## After First Deployment

### Add Missing Secrets

After your first deployment, add these GitHub secrets:

```
APP_RUNNER_SERVICE_ARN=arn:aws:apprunner:us-east-1:ACCOUNT:service/better-call-buffet-prod/SERVICE_ID
PROD_APP_URL=https://your-service-url.awsapprunner.com
```

Get these from AWS Console → App Runner → your service.

### Test Your API

```bash
# Health check
curl https://your-service-url.awsapprunner.com/health

# API endpoints
curl https://your-service-url.awsapprunner.com/api/v1/accounts
curl https://your-service-url.awsapprunner.com/api/v1/users
```

### Set Up Monitoring

1. **AWS Console** → **CloudWatch** → **Alarms**
2. Monitor your App Runner service
3. Set up alerts for errors/performance

---

## Cost Estimates

**Monthly AWS costs** (approximate):

- **App Runner**: $15-30/month (depending on usage)
- **RDS db.t3.micro**: $15-20/month
- **ECR storage**: $1-5/month
- **Total**: ~$30-55/month

---

## Next Steps (After Production)

- [ ] Set up custom domain
- [ ] Add SSL certificate
- [ ] Configure monitoring alerts
- [ ] Set up staging environment
- [ ] Plan backup strategy
- [ ] Security review

---

## Quick Commands Reference

```bash
# Check deployment status
aws apprunner list-services

# View App Runner logs
aws logs tail /aws/apprunner/better-call-buffet-prod --follow

# Check RDS status
aws rds describe-db-instances --db-instance-identifier bcb-db

# Test database connection
python utilities/test_db_connection.py
```

---

**🎯 Goal**: Get your API running in production in 15 minutes!

**Questions?** Check the logs in GitHub Actions or AWS Console.
