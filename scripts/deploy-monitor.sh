#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "🚀 Starting Better Call Buffet deployment monitoring..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to send notification (webhook/slack/email)
send_notification() {
    local status="$1"
    local message="$2"
    local emoji="$3"
    
    echo -e "${emoji} ${message}"
    
    # Optional: Add webhook notification here
    # curl -X POST -H 'Content-type: application/json' \
    #   --data "{\"text\":\"${emoji} Better Call Buffet: ${message}\"}" \
    #   $SLACK_WEBHOOK_URL
}

# Pre-deployment checks
echo "📋 Running pre-deployment checks..."

# Check if we have pending migrations
echo "🔍 Checking for pending migrations..."
if docker-compose exec -T web alembic heads | grep -q "^[a-f0-9]"; then
    echo "✅ Migration heads found"
else
    send_notification "warning" "No migration heads found - this might be expected" "⚠️"
fi

# Health check function
health_check() {
    local max_attempts=30
    local attempt=1
    
    echo "🏥 Waiting for application to be healthy..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "https://better-call-buffet-prod.fly.dev/health" > /dev/null 2>&1; then
            send_notification "success" "Application is healthy and responding!" "✅"
            return 0
        fi
        
        echo "Attempt $attempt/$max_attempts - waiting 10s..."
        sleep 10
        ((attempt++))
    done
    
    send_notification "error" "Application failed health check after deployment" "❌"
    return 1
}

# Deploy function
deploy() {
    echo "🚀 Starting deployment..."
    send_notification "info" "Deployment started" "🚀"
    
    # Deploy to Fly.io
    if fly deploy --app better-call-buffet-prod --verbose; then
        send_notification "success" "Deployment completed successfully" "✅"
        
        # Run health check
        if health_check; then
            echo "🎉 Deployment successful and healthy!"
            send_notification "success" "Full deployment successful - application is live!" "🎉"
        else
            echo "❌ Deployment completed but health check failed"
            send_notification "error" "Deployment completed but application is not healthy" "❌"
            return 1
        fi
    else
        send_notification "error" "Deployment failed" "❌"
        echo "❌ Deployment failed!"
        return 1
    fi
}

# Main execution
echo "🎯 Better Call Buffet Production Deployment"
echo "=========================================="

# Run deployment
if deploy; then
    echo -e "${GREEN}✅ All deployment steps completed successfully!${NC}"
    
    # Show deployment info
    echo ""
    echo "📊 Deployment Summary:"
    echo "- App URL: https://better-call-buffet-prod.fly.dev"
    echo "- Health endpoint: https://better-call-buffet-prod.fly.dev/health"
    echo "- Logs: fly logs"
    echo "- Monitoring: fly status"
    
    exit 0
else
    echo -e "${RED}❌ Deployment failed!${NC}"
    echo ""
    echo "🔧 Troubleshooting steps:"
    echo "1. Check logs: fly logs"
    echo "2. Check status: fly status"
    echo "3. Check migrations: fly ssh console -C 'alembic current'"
    echo "4. Rollback if needed: fly releases"
    
    exit 1
fi