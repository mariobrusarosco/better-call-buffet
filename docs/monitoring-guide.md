# 📊 Better Call Buffet - Production Monitoring Guide

Complete guide for monitoring your production API and debugging issues.

## 🔍 Quick Debugging Commands

### Immediate Issue Investigation
```bash
# Check if app is running
fly status --app better-call-buffet-prod

# Real-time logs (follow mode)
fly logs --app better-call-buffet-prod -f

# Search for errors in recent logs
fly logs --app better-call-buffet-prod --search "error"
fly logs --app better-call-buffet-prod --search "500"
fly logs --app better-call-buffet-prod --search "exception"

# Check specific time window
fly logs --app better-call-buffet-prod --since 1h
fly logs --app better-call-buffet-prod --since 30m
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

### 1. Fly.io Grafana Dashboard
- **URL:** https://fly.io/apps/better-call-buffet-prod/monitoring
- **Metrics Available:**
  - CPU usage
  - Memory consumption
  - HTTP request count
  - Response times
  - Error rates

### 2. App Overview Dashboard
- **URL:** https://fly.io/apps/better-call-buffet-prod
- **Features:**
  - Machine status
  - Recent deployments
  - SSL certificates
  - Secrets management

## 🚨 Error Investigation Workflow

### Step 1: Check App Status
```bash
fly status --app better-call-buffet-prod
```

### Step 2: Review Recent Logs
```bash
# Look for errors in last 30 minutes
fly logs --app better-call-buffet-prod --since 30m | grep -i "error\|exception\|traceback"
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
fly secrets list --app better-call-buffet-prod
```

### Step 5: Database Connection (if needed)
```bash
# Connect to production environment
fly ssh console --app better-call-buffet-prod

# Inside the container, test database
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
fly secrets list --app better-call-buffet-prod | grep DATABASE_URL

# Test database connection
fly ssh console --app better-call-buffet-prod -C "python -c 'from app.core.config import settings; print(settings.DATABASE_URL[:50])'"
```

### CORS Issues
```bash
# Check CORS configuration
fly secrets list --app better-call-buffet-prod | grep CORS

# Test CORS
curl -H "Origin: https://yourfrontend.com" \
     -H "Access-Control-Request-Method: GET" \
     -H "Access-Control-Request-Headers: X-Requested-With" \
     -X OPTIONS \
     https://api-better-call-buffet.mariobrusarosco.com/health
```

### Migration Issues
```bash
# Check current migration status
fly ssh console --app better-call-buffet-prod -C "alembic current"

# Run migrations manually (if needed)
fly ssh console --app better-call-buffet-prod -C "alembic upgrade head"
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
time curl https://api-better-call-buffet.mariobrusarosco.com/health

# Continuous monitoring
./scripts/monitoring-alerts.sh watch
```

### Resource Usage
- Monitor via Grafana: https://fly.io/apps/better-call-buffet-prod/monitoring
- Check machine status: `fly status --app better-call-buffet-prod`

## 🚀 Scaling & Performance

### Auto-scaling Configuration
Your app is configured for auto-scaling:
- `min_machines_running = 0` (scales to zero when not in use)
- `auto_start_machines = true` (starts automatically on requests)
- `auto_stop_machines = 'stop'` (stops when idle)

### Manual Scaling
```bash
# Scale up
fly scale count 2 --app better-call-buffet-prod

# Scale down
fly scale count 1 --app better-call-buffet-prod

# Check current scale
fly status --app better-call-buffet-prod
```

## 📱 Mobile Monitoring

### Quick Health Check Script
Create this alias in your `~/.bashrc` or `~/.zshrc`:

```bash
alias bcb-health='curl -s https://api-better-call-buffet.mariobrusarosco.com/health && echo " ✅ API is healthy"'
alias bcb-logs='fly logs --app better-call-buffet-prod -f'
alias bcb-status='fly status --app better-call-buffet-prod'
```

## 🎯 Summary

**Your monitoring stack:**
- ✅ **Real-time logs:** `fly logs -f`
- ✅ **Grafana metrics:** Built-in dashboard
- ✅ **Health monitoring:** Custom script
- ✅ **Error alerting:** Monitoring script with notification hooks
- ✅ **Performance tracking:** Response time monitoring
- ✅ **Structured logging:** JSON format with all details

**When issues occur:**
1. Run `./scripts/monitoring-alerts.sh all`
2. Check `fly logs --app better-call-buffet-prod --since 30m`
3. Review Grafana dashboard
4. Test API endpoints directly

**Need help?** Check the error investigation workflow above! 🚀