# Production Database Migration Strategy

## 🎓 Overview

This guide explains our production database migration strategy for the Better Call Buffet application, designed to ensure zero-downtime deployments and robust database schema management.

## 🏗️ Architecture

### Migration Flow

```
GitHub Push → Build Image → Run Migrations → Deploy to App Runner
     ↓              ↓              ↓              ↓
   Trigger      Docker Build   Schema Update   App Start
   Workflow     & Push to ECR   (Separate)     (Fast)
```

### Key Components

1. **`scripts/run-migrations.sh`** - Dedicated migration script
2. **`scripts/run-prod.sh`** - Fast application startup (no migrations)
3. **GitHub Actions** - Orchestrates migration before deployment
4. **AWS Secrets Manager** - Provides database credentials securely

## 🔄 How It Works

### Before (Problematic Approach)

```bash
Container Start → Run Migrations → Start App
     ↓                  ↓             ↓
  Slow startup     Timeout risk   Failed deploy
```

**Problems:**

- ❌ Container startup timeouts
- ❌ Race conditions with multiple instances
- ❌ Failed deployments if migrations fail
- ❌ Long-running migrations block app startup

### After (Production-Ready Approach)

```bash
# Step 1: Build and push image
Docker Build → Push to ECR

# Step 2: Run migrations (separate container)
Migration Container → Connect to DB → Run Alembic → Exit

# Step 3: Deploy application (fast startup)
App Runner → Pull Image → Start App (no migrations)
```

**Benefits:**

- ✅ Fast application startup
- ✅ Migrations run once per deployment
- ✅ Better error handling and rollback
- ✅ No container startup timeouts
- ✅ Separation of concerns

## 📋 Migration Process

### 1. Pre-Deployment Migration (Automated)

When you push to `main`, GitHub Actions automatically:

```yaml
- name: Run Database Migrations
  run: |
    docker run --rm \
      -e ENVIRONMENT=production \
      -e AWS_DEFAULT_REGION=us-east-2 \
      -e AWS_ACCESS_KEY_ID \
      -e AWS_SECRET_ACCESS_KEY \
      -e AWS_SESSION_TOKEN \
      895583929848.dkr.ecr.us-east-2.amazonaws.com/better-call-buffet:latest \
      /app/scripts/run-migrations.sh
```

### 2. Migration Script Details

The `run-migrations.sh` script:

1. **Tests database connectivity**
2. **Runs Alembic migrations**
3. **Shows current migration status**
4. **Exits with proper error codes**

### 3. Application Deployment

After successful migrations, App Runner deploys the application with:

- Fast startup (no migration delays)
- Health checks pass quickly
- Zero-downtime deployment

## 🛠️ Manual Migration Commands

### Run Migrations Manually

If you need to run migrations outside of the deployment process:

```bash
# Using Docker locally
docker run --rm \
  -e ENVIRONMENT=production \
  -e AWS_DEFAULT_REGION=us-east-2 \
  -e AWS_ACCESS_KEY_ID=your_key \
  -e AWS_SECRET_ACCESS_KEY=your_secret \
  better-call-buffet:latest \
  /app/scripts/run-migrations.sh

# Or connect to production database directly
export DATABASE_URL="postgresql://user:pass@host:5432/db"
alembic upgrade head
```

### Check Migration Status

```bash
# Show current migration version
alembic current

# Show migration history
alembic history

# Show pending migrations
alembic show head
```

### Rollback Migrations

```bash
# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade abc123

# Rollback all migrations (dangerous!)
alembic downgrade base
```

## 🚨 Emergency Procedures

### Failed Migration During Deployment

If migrations fail during GitHub Actions:

1. **Check the logs** in GitHub Actions
2. **Fix the migration issue** locally
3. **Test the fix** with local database
4. **Push the fix** to trigger new deployment

### Rollback Strategy

If you need to rollback after deployment:

1. **Create a down migration** to undo changes
2. **Test locally** first
3. **Run manually** if urgent:
   ```bash
   alembic downgrade -1
   ```
4. **Deploy the rollback** through normal process

### Database Connection Issues

If migrations can't connect to the database:

1. **Check AWS Secrets Manager** has correct DATABASE_URL
2. **Verify RDS instance** is running and accessible
3. **Check security groups** allow connections
4. **Test connection** manually:
   ```bash
   psql "postgresql://user:pass@host:5432/db"
   ```

## 📊 Monitoring and Logging

### GitHub Actions Logs

Monitor migration success in GitHub Actions:

- ✅ "Database connection successful"
- ✅ "Database migrations completed successfully"
- ❌ Any error messages for troubleshooting

### Database Monitoring

Set up CloudWatch alarms for:

- **Connection count spikes** during migrations
- **Long-running queries** from Alembic
- **Database locks** that might indicate issues

### Application Health

After deployment, verify:

- App Runner health checks pass
- Application starts quickly
- No database connection errors in logs

## 🔧 Development Workflow

### Creating New Migrations

1. **Develop locally** with your changes
2. **Generate migration**:
   ```bash
   alembic revision --autogenerate -m "Add new feature"
   ```
3. **Review the migration** file carefully
4. **Test locally**:
   ```bash
   alembic upgrade head
   alembic downgrade -1  # Test rollback
   alembic upgrade head  # Test forward again
   ```
5. **Commit and push** - migrations run automatically

### Testing Migrations

Always test migrations with realistic data:

```bash
# Create test database with production-like data
pg_dump production_db | psql test_db

# Test migration on test database
DATABASE_URL="postgresql://localhost/test_db" alembic upgrade head

# Verify data integrity
# Run your application tests
# Test rollback if needed
```

## 🎯 Best Practices

### Migration Safety

1. **Backward Compatible**: New migrations shouldn't break running instances
2. **Idempotent**: Migrations should be safe to run multiple times
3. **Tested**: Always test migrations locally first
4. **Small Changes**: Prefer many small migrations over large ones
5. **Data Preservation**: Never delete data without backup strategy

### Performance Considerations

1. **Index Creation**: Use `CONCURRENTLY` for large tables
2. **Batch Updates**: Process large data changes in batches
3. **Lock Duration**: Minimize table lock time
4. **Off-Peak Timing**: Run heavy migrations during low traffic

### Monitoring

1. **Migration Duration**: Track how long migrations take
2. **Error Rates**: Monitor for migration failures
3. **Database Performance**: Watch for performance impact
4. **Application Health**: Ensure app remains healthy during migrations

## 🔗 Related Documentation

- [Database Connection Guide](./database-connection-guide.md)
- [AWS Secrets Manager Setup](./aws-secrets-setup.md)
- [Production Deployment Guide](./production-deployment-guide.md)
- [Troubleshooting Guide](./troubleshooting-guide.md)

---

**💡 Educational Insight**: This migration strategy demonstrates production-grade database management practices used by major companies. Understanding separation of concerns between schema changes and application deployment is crucial for scalable backend systems.
