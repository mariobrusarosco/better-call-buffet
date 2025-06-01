#!/bin/bash

# Script to create a CloudWatch dashboard for Elastic Beanstalk monitoring

set -e  # Exit on error

# Configuration
APP_NAME="better-call-buffet"
ENV_NAME="better-call-buffet-prod"
DASHBOARD_NAME="BetterCallBuffet-Dashboard"
REGION=$(aws configure get region)

echo "====== Creating CloudWatch Dashboard for Elastic Beanstalk ======"
echo "Application: $APP_NAME"
echo "Environment: $ENV_NAME"
echo "Dashboard: $DASHBOARD_NAME"
echo "Region: $REGION"

# First, get the environment ID
echo "Getting environment ID..."
ENV_ID=$(aws elasticbeanstalk describe-environments \
    --environment-names "$ENV_NAME" \
    --region "$REGION" \
    --query "Environments[0].EnvironmentId" \
    --output text)

if [ -z "$ENV_ID" ] || [ "$ENV_ID" == "None" ]; then
    echo "Error: Could not find environment ID for $ENV_NAME"
    exit 1
fi

echo "Environment ID: $ENV_ID"

# Create dashboard JSON
echo "Creating dashboard JSON..."
cat > dashboard.json << EOL
{
    "widgets": [
        {
            "type": "text",
            "x": 0,
            "y": 0,
            "width": 24,
            "height": 2,
            "properties": {
                "markdown": "# Better Call Buffet - Elastic Beanstalk Monitoring\nEnvironment: $ENV_NAME | Region: $REGION | Environment ID: $ENV_ID"
            }
        },
        {
            "type": "metric",
            "x": 0,
            "y": 2,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/ElasticBeanstalk", "EnvironmentHealth", "EnvironmentName", "$ENV_NAME" ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "$REGION",
                "title": "Environment Health",
                "period": 300,
                "stat": "Average"
            }
        },
        {
            "type": "metric",
            "x": 12,
            "y": 2,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/EC2", "CPUUtilization", "AutoScalingGroupName", "$ENV_NAME-asg" ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "$REGION",
                "title": "CPU Utilization",
                "period": 300,
                "stat": "Average"
            }
        },
        {
            "type": "metric",
            "x": 0,
            "y": 8,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/EC2", "NetworkIn", "AutoScalingGroupName", "$ENV_NAME-asg" ],
                    [ "AWS/EC2", "NetworkOut", "AutoScalingGroupName", "$ENV_NAME-asg" ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "$REGION",
                "title": "Network Traffic",
                "period": 300,
                "stat": "Average"
            }
        },
        {
            "type": "metric",
            "x": 12,
            "y": 8,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/ApplicationELB", "RequestCount", "LoadBalancer", "$ENV_NAME-alb" ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "$REGION",
                "title": "Request Count",
                "period": 300,
                "stat": "Sum"
            }
        },
        {
            "type": "metric",
            "x": 0,
            "y": 14,
            "width": 8,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/ApplicationELB", "HTTPCode_Target_2XX_Count", "LoadBalancer", "$ENV_NAME-alb" ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "$REGION",
                "title": "2XX Responses",
                "period": 300,
                "stat": "Sum"
            }
        },
        {
            "type": "metric",
            "x": 8,
            "y": 14,
            "width": 8,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/ApplicationELB", "HTTPCode_Target_4XX_Count", "LoadBalancer", "$ENV_NAME-alb" ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "$REGION",
                "title": "4XX Responses",
                "period": 300,
                "stat": "Sum"
            }
        },
        {
            "type": "metric",
            "x": 16,
            "y": 14,
            "width": 8,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/ApplicationELB", "HTTPCode_Target_5XX_Count", "LoadBalancer", "$ENV_NAME-alb" ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "$REGION",
                "title": "5XX Responses",
                "period": 300,
                "stat": "Sum"
            }
        },
        {
            "type": "metric",
            "x": 0,
            "y": 20,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", "$ENV_NAME-alb" ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "$REGION",
                "title": "Response Time",
                "period": 300,
                "stat": "Average"
            }
        },
        {
            "type": "metric",
            "x": 12,
            "y": 20,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", "bcb-db" ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "$REGION",
                "title": "RDS CPU Utilization",
                "period": 300,
                "stat": "Average"
            }
        }
    ]
}
EOL

# Create or update the dashboard
echo "Creating/updating CloudWatch dashboard..."
aws cloudwatch put-dashboard \
    --dashboard-name "$DASHBOARD_NAME" \
    --dashboard-body file://dashboard.json \
    --region "$REGION"

# Clean up temporary files
rm dashboard.json

echo "====== CloudWatch Dashboard Created ======"
echo "Dashboard name: $DASHBOARD_NAME"
echo "You can view it in the CloudWatch console under Dashboards" 