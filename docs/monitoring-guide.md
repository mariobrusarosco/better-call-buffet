# 📊 Better Call Buffet - Production Monitoring Guide

Complete guide for monitoring your production API and debugging issues.

## 🔍 Quick Debugging Commands

### Immediate Issue Investigation
```bash
# Check if app is running
railway status

# Real-time logs (follow mode)
railway logs

# Search for errors in recent logs
railway logs | grep -i "error"
railway logs | grep -i "500"
railway logs | grep -i "exception"

# Check service status
railway service
```

### Health Check & Performance
```bash
# Test your API directly
curl https://api-better-call-buffet.mariobrusarosco.com/health

# Run monitoring script
./scripts/monitoring-alerts.sh all          # All checks
./scripts/monitoring-alerts.sh health       # Health only
./scripts/monitoring-alerts.sh errors       # Error check
./scripts/monitoring-alerts.sh watch        # Continuous monitoring
```

## 📈 Monitoring Dashboards

### 1. Railway Dashboard
- **URL:** https://railway.app/dashboard
- **Metrics Available:**
  - CPU usage
  - Memory consumption
  - HTTP request count
  - Response times
  - Error rates

### 2. Service Overview
- **URL:** Railway project dashboard
- **Features:**
  - Service status
  - Recent deployments
  - Environment variables
  - Build logs

## 🚨 Error Investigation Workflow

### Step 1: Check Service Status
```bash
railway status
```

### Step 2: Review Recent Logs
```bash
# Look for errors in recent logs
railway logs | grep -i "error\|exception\|traceback"
```

### Step 3: Test API Endpoints
```bash
# Test health endpoint
curl -v https://api-better-call-buffet.mariobrusarosco.com/health

# Test specific failing endpoint
curl -v https://api-better-call-buffet.mariobrusarosco.com/api/v1/your-endpoint
```

### Step 4: Check Environment Variables
```bash
railway variables
```

### Step 5: Database Connection (if needed)
```bash
# Connect to production environment via Railway CLI
railway shell

# Inside the shell, test database
python -c "
from app.core.config import settings
from sqlalchemy import create_engine, text
engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    result = conn.execute(text('SELECT version()'))
    print('DB Connected:', result.fetchone()[0])
"
```

## 🔧 Common Issues & Solutions

### Database Connection Issues
```bash
# Check if DATABASE_URL is set
railway variables | grep DATABASE_URL

# Test database connection
railway shell "python -c 'from app.core.config import settings; print(settings.DATABASE_URL[:50])'"
```

### CORS Issues
```bash
# Check CORS configuration
railway variables | grep CORS

# Test CORS
curl -H "Origin: https://yourfrontend.com" \
     -H "Access-Control-Request-Method: GET" \
     -H "Access-Control-Request-Headers: X-Requested-With" \
     -X OPTIONS \
     https://your-app.railway.app/health
```

### Migration Issues
```bash
# Check current migration status
railway shell "alembic current"

# Run migrations manually (if needed)
railway shell "alembic upgrade head"
```

## 📧 Setting Up Alerts (Optional)

### Webhook Notifications
Edit `scripts/monitoring-alerts.sh` and uncomment the webhook section:

```bash
# Add your webhook URL (Slack, Discord, etc.)
WEBHOOK_URL="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"

# The script will automatically send notifications
```

### Email Alerts via Fly.io
```bash
# Set up email notifications (requires Fly.io paid plan)
fly apps create better-call-buffet-alerts
fly deploy --app better-call-buffet-alerts
```

## 📊 Performance Monitoring

### Response Time Monitoring
```bash
# Check response times
time curl https://your-app.railway.app/health

# Continuous monitoring
./scripts/monitoring-alerts.sh watch
```

### Resource Usage
- Monitor via Railway dashboard: https://railway.app/dashboard
- Check service status: `railway status`

## 🚀 Scaling & Performance

### Auto-scaling Configuration
Your app is configured for auto-scaling:
- Railway automatically handles scaling based on demand
- Zero-downtime deployments
- Automatic resource allocation

### Resource Management
```bash
# Check service status
railway status

# View service logs
railway logs

# Check resource usage
railway service
```

## 📱 Mobile Monitoring

### Quick Health Check Script
Create this alias in your `~/.bashrc` or `~/.zshrc`:

```bash
alias bcb-health='curl -s https://your-app.railway.app/health && echo " ✅ API is healthy"'
alias bcb-logs='railway logs'
alias bcb-status='railway status'
```

## 🎯 Summary

**Your monitoring stack:**
- ✅ **Real-time logs:** `railway logs`
- ✅ **Railway metrics:** Built-in dashboard
- ✅ **Health monitoring:** Custom script
- ✅ **Error alerting:** Monitoring script with notification hooks
- ✅ **Performance tracking:** Response time monitoring
- ✅ **Structured logging:** JSON format with all details

**When issues occur:**
1. Run `./scripts/monitoring-alerts.sh all`
2. Check `railway logs`
3. Review Railway dashboard
4. Test API endpoints directly

**Need help?** Check the error investigation workflow above! 🚀