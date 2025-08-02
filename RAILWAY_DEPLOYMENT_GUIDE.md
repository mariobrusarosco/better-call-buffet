# Railway Deployment Guide

## Prerequisites

1. **Railway Account**: Sign up at [railway.app](https://railway.app)
2. **GitHub Integration**: Connect your GitHub account to Railway
3. **Push Changes**: Ensure all changes are committed and pushed to your GitHub repository

## Step 1: Deploy PostgreSQL Database

1. **Create New Project** in Railway dashboard
2. **Add Service** → **Database** → **PostgreSQL**
3. **Note**: Railway will automatically generate a `DATABASE_URL` environment variable

## Step 2: Deploy FastAPI Application

### Option A: GitHub Repository Deploy (Recommended)

1. **Add Service** → **GitHub Repo**
2. **Select Repository**: `better-call-buffet`
3. **Branch**: Select your main branch
4. **Deploy**: Railway will automatically detect the Dockerfile and `railway.toml`

### Option B: CLI Deploy

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Link to your project
railway link

# Deploy
railway up
```

## Step 3: Configure Environment Variables

In Railway dashboard, go to your web service and add these environment variables:

```
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-super-secure-secret-key-here
BACKEND_CORS_ORIGINS=["https://yourdomain.railway.app"]
SENTRY_DSN=your-sentry-dsn-here
ENABLE_PERFORMANCE_LOGGING=true
```

**Important**: 
- `DATABASE_URL` is automatically provided by Railway PostgreSQL service
- `PORT` is automatically set by Railway
- Update `BACKEND_CORS_ORIGINS` with your actual domain after deployment

## Step 4: Database Migration

Railway will automatically run your migration script (`./scripts/run-migrations.sh`) during deployment due to the Dockerfile CMD configuration.

If you need to run migrations manually:
```bash
railway run ./scripts/run-migrations.sh
```

## Step 5: Generate Domain

1. **Go to Settings** in your web service
2. **Generate Domain** to get a public URL like `your-app-name.railway.app`
3. **Update CORS**: Add the generated domain to `BACKEND_CORS_ORIGINS`

## Step 6: Verify Deployment

1. **Check Logs**: Monitor deployment logs in Railway dashboard
2. **Test Health Endpoint**: Visit `https://your-app.railway.app/health`
3. **Test API**: Visit `https://your-app.railway.app/docs` for FastAPI documentation

## Monitoring and Maintenance

### View Logs
```bash
railway logs
```

### Monitor Metrics
- Railway dashboard provides CPU, Memory, and Network metrics
- Set up alerts for critical metrics

### Rollback
- Railway provides instant rollback functionality
- Use the dashboard to rollback to previous deployments

## Differences from Fly.io

1. **Server**: Now using Hypercorn instead of Uvicorn (Railway recommended)
2. **Scaling**: Automatic resource management (no manual configuration needed)
3. **Database**: Managed PostgreSQL service with automatic `DATABASE_URL`
4. **Monitoring**: Built-in metrics and logging in Railway dashboard
5. **CI/CD**: Automatic deployments on GitHub pushes

## Cost Considerations

- **Free Tier**: Available for small applications
- **Pro Plan**: $5/month per user, includes more resources and priority support
- **Usage-Based**: Billing based on actual resource consumption

## Support

- Railway provides excellent documentation at [docs.railway.app](https://docs.railway.app)
- Community support on Discord
- Email support for Pro plan users