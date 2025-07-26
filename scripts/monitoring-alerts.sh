#!/bin/bash

# Better Call Buffet - Production Monitoring Script
# Run this locally to monitor your production app

APP_NAME="better-call-buffet-prod"
HEALTH_URL="https://api-better-call-buffet.mariobrusarosco.com/health"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🎯 Better Call Buffet Production Monitor"
echo "========================================"

# Function to send notification (customize as needed)
send_alert() {
    local severity="$1"
    local message="$2"
    local emoji="$3"
    
    echo -e "${emoji} [$(date)] ${severity}: ${message}"
    
    # Optional: Add webhook/Slack/Discord notification here
    # curl -X POST -H 'Content-type: application/json' \
    #   --data "{\"text\":\"${emoji} Better Call Buffet ${severity}: ${message}\"}" \
    #   $WEBHOOK_URL
}

# Health check monitoring
monitor_health() {
    echo "🏥 Checking application health..."
    
    if curl -s -f "$HEALTH_URL" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Application is healthy${NC}"
        return 0
    else
        send_alert "CRITICAL" "Application health check failed!" "🚨"
        return 1
    fi
}

# Error log monitoring
monitor_errors() {
    echo "📋 Checking for recent errors..."
    
    # Get logs from last 5 minutes and check for errors
    if fly logs --app $APP_NAME --since 5m | grep -i "error\|exception\|500\|failed" > /dev/null; then
        send_alert "WARNING" "Errors detected in recent logs" "⚠️"
        echo "🔍 Recent errors:"
        fly logs --app $APP_NAME --since 5m | grep -i "error\|exception\|500\|failed" | tail -5
    else
        echo -e "${GREEN}✅ No recent errors detected${NC}"
    fi
}

# Performance monitoring
monitor_performance() {
    echo "📊 Checking application performance..."
    
    # Simple response time check
    response_time=$(curl -o /dev/null -s -w "%{time_total}" "$HEALTH_URL")
    
    if (( $(echo "$response_time > 2.0" | bc -l) )); then
        send_alert "WARNING" "Slow response time: ${response_time}s" "🐌"
    else
        echo -e "${GREEN}✅ Response time OK: ${response_time}s${NC}"
    fi
}

# Main monitoring loop
case "${1:-all}" in
    "health")
        monitor_health
        ;;
    "errors")
        monitor_errors
        ;;
    "performance")
        monitor_performance
        ;;
    "all")
        monitor_health
        monitor_errors
        monitor_performance
        ;;
    "watch")
        echo "👀 Starting continuous monitoring (every 30s)..."
        while true; do
            echo ""
            echo "=== $(date) ==="
            monitor_health
            monitor_errors
            echo "Sleeping 30s..."
            sleep 30
        done
        ;;
    *)
        echo "Usage: $0 {health|errors|performance|all|watch}"
        echo ""
        echo "Examples:"
        echo "  $0 health      - Check health only"
        echo "  $0 errors      - Check for errors"
        echo "  $0 all         - Run all checks"
        echo "  $0 watch       - Continuous monitoring"
        exit 1
        ;;
esac

echo ""
echo "📊 Quick Status Commands:"
echo "  fly status --app $APP_NAME"
echo "  fly logs --app $APP_NAME -f"
echo "  fly dashboard --app $APP_NAME"