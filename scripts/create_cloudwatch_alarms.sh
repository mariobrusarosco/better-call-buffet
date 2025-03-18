#!/bin/bash

# Script to create CloudWatch alarms for the Better Call Buffet application

set -e  # Exit on error

# Configuration
APP_NAME="better-call-buffet"
ENV_NAME="better-call-buffet-prod"
ASG_NAME="$ENV_NAME-asg"
ALB_NAME="$ENV_NAME-alb"
DB_INSTANCE="bcb-db"
REGION=$(aws configure get region)

# Create or get SNS topic for alerts
echo "Setting up SNS topic for alarms..."
SNS_TOPIC_NAME="BCB-Alerts"
SNS_TOPIC_ARN=$(aws sns list-topics --query "Topics[?contains(TopicArn, \`$SNS_TOPIC_NAME\`)].TopicArn" --output text)

if [ -z "$SNS_TOPIC_ARN" ] || [ "$SNS_TOPIC_ARN" == "None" ]; then
    echo "Creating SNS topic: $SNS_TOPIC_NAME"
    SNS_TOPIC_ARN=$(aws sns create-topic --name "$SNS_TOPIC_NAME" --query 'TopicArn' --output text)
    
    # You'd typically add subscription here
    # aws sns subscribe --topic-arn "$SNS_TOPIC_ARN" --protocol email --notification-endpoint alerts@example.com
else
    echo "Using existing SNS topic: $SNS_TOPIC_ARN"
fi

echo "====== Creating CloudWatch Alarms ======"

# Check if the Elastic Beanstalk environment exists
echo "Checking Elastic Beanstalk environment..."
EB_ENV=$(aws elasticbeanstalk describe-environments --environment-names "$ENV_NAME" --query "Environments[0]" --output json)

if [ -z "$EB_ENV" ] || [ "$EB_ENV" == "null" ]; then
    echo "Warning: Elastic Beanstalk environment $ENV_NAME not found"
    echo "Please create the environment first or check the name"
    echo "Continuing with alarm creation anyway..."
fi

# Check if the RDS instance exists
echo "Checking RDS instance..."
RDS_INSTANCE=$(aws rds describe-db-instances --db-instance-identifier "$DB_INSTANCE" --query "DBInstances[0]" --output json 2>/dev/null || echo "")

if [ -z "$RDS_INSTANCE" ] || [ "$RDS_INSTANCE" == "null" ]; then
    echo "Warning: RDS instance $DB_INSTANCE not found"
    echo "Please create the RDS instance first or check the name"
    echo "Continuing with alarm creation anyway..."
fi

# Create infrastructure alarms
echo "Creating Infrastructure Alarms..."

# Environment Health
aws cloudwatch put-metric-alarm \
  --alarm-name "BCB-Prod-EnvironmentHealth" \
  --alarm-description "Alarm when environment health is not Green" \
  --metric-name "EnvironmentHealth" \
  --namespace "AWS/ElasticBeanstalk" \
  --statistic "Average" \
  --period 300 \
  --threshold 40 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions Name=EnvironmentName,Value="$ENV_NAME" \
  --evaluation-periods 1 \
  --alarm-actions "$SNS_TOPIC_ARN" \
  --ok-actions "$SNS_TOPIC_ARN" \
  --region "$REGION"

echo "Created Environment Health alarm"

# CPU Utilization
aws cloudwatch put-metric-alarm \
  --alarm-name "BCB-Prod-HighCPUUtilization" \
  --alarm-description "Alarm when CPU exceeds 70% for 5 minutes" \
  --metric-name "CPUUtilization" \
  --namespace "AWS/EC2" \
  --statistic "Average" \
  --period 300 \
  --threshold 70 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions Name=AutoScalingGroupName,Value="$ASG_NAME" \
  --evaluation-periods 1 \
  --alarm-actions "$SNS_TOPIC_ARN" \
  --ok-actions "$SNS_TOPIC_ARN" \
  --region "$REGION"

echo "Created CPU Utilization alarm"

# Memory Utilization
aws cloudwatch put-metric-alarm \
  --alarm-name "BCB-Prod-HighMemoryUtilization" \
  --alarm-description "Alarm when Memory exceeds 80% for 5 minutes" \
  --metric-name "MemoryUtilization" \
  --namespace "AWS/ElasticBeanstalk" \
  --statistic "Average" \
  --period 300 \
  --threshold 80 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions Name=EnvironmentName,Value="$ENV_NAME" \
  --evaluation-periods 1 \
  --alarm-actions "$SNS_TOPIC_ARN" \
  --ok-actions "$SNS_TOPIC_ARN" \
  --region "$REGION"

echo "Created Memory Utilization alarm"

# Create application performance alarms
echo "Creating Application Performance Alarms..."

# 5XX Error Rate
aws cloudwatch put-metric-alarm \
  --alarm-name "BCB-Prod-High5XXErrors" \
  --alarm-description "Alarm when 5XX errors exceed 10 per minute" \
  --metric-name "HTTPCode_Target_5XX_Count" \
  --namespace "AWS/ApplicationELB" \
  --statistic "Sum" \
  --period 60 \
  --threshold 10 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions Name=LoadBalancer,Value="$ALB_NAME" \
  --evaluation-periods 1 \
  --alarm-actions "$SNS_TOPIC_ARN" \
  --ok-actions "$SNS_TOPIC_ARN" \
  --region "$REGION"

echo "Created 5XX Error Rate alarm"

# Response Time
aws cloudwatch put-metric-alarm \
  --alarm-name "BCB-Prod-HighResponseTime" \
  --alarm-description "Alarm when response time exceeds 2 seconds" \
  --metric-name "TargetResponseTime" \
  --namespace "AWS/ApplicationELB" \
  --statistic "Average" \
  --period 300 \
  --threshold 2 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions Name=LoadBalancer,Value="$ALB_NAME" \
  --evaluation-periods 1 \
  --alarm-actions "$SNS_TOPIC_ARN" \
  --ok-actions "$SNS_TOPIC_ARN" \
  --region "$REGION"

echo "Created Response Time alarm"

# Request Count
aws cloudwatch put-metric-alarm \
  --alarm-name "BCB-Prod-LowRequestCount" \
  --alarm-description "Alarm when request count is too low (potential outage)" \
  --metric-name "RequestCount" \
  --namespace "AWS/ApplicationELB" \
  --statistic "Sum" \
  --period 300 \
  --threshold 10 \
  --comparison-operator "LessThanThreshold" \
  --dimensions Name=LoadBalancer,Value="$ALB_NAME" \
  --evaluation-periods 3 \
  --alarm-actions "$SNS_TOPIC_ARN" \
  --ok-actions "$SNS_TOPIC_ARN" \
  --region "$REGION"

echo "Created Request Count alarm"

# Create database alarms
echo "Creating Database Alarms..."

# RDS CPU Utilization
aws cloudwatch put-metric-alarm \
  --alarm-name "BCB-DB-HighCPUUtilization" \
  --alarm-description "Alarm when RDS CPU exceeds 80% for 5 minutes" \
  --metric-name "CPUUtilization" \
  --namespace "AWS/RDS" \
  --statistic "Average" \
  --period 300 \
  --threshold 80 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions Name=DBInstanceIdentifier,Value="$DB_INSTANCE" \
  --evaluation-periods 1 \
  --alarm-actions "$SNS_TOPIC_ARN" \
  --ok-actions "$SNS_TOPIC_ARN" \
  --region "$REGION"

echo "Created RDS CPU Utilization alarm"

# RDS Free Storage Space
aws cloudwatch put-metric-alarm \
  --alarm-name "BCB-DB-LowFreeStorageSpace" \
  --alarm-description "Alarm when free storage space is below 10GB" \
  --metric-name "FreeStorageSpace" \
  --namespace "AWS/RDS" \
  --statistic "Average" \
  --period 300 \
  --threshold 10000000000 \
  --comparison-operator "LessThanThreshold" \
  --dimensions Name=DBInstanceIdentifier,Value="$DB_INSTANCE" \
  --evaluation-periods 1 \
  --alarm-actions "$SNS_TOPIC_ARN" \
  --ok-actions "$SNS_TOPIC_ARN" \
  --region "$REGION"

echo "Created RDS Free Storage Space alarm"

# RDS Connection Count
aws cloudwatch put-metric-alarm \
  --alarm-name "BCB-DB-HighConnectionCount" \
  --alarm-description "Alarm when database connections exceed 80% of maximum" \
  --metric-name "DatabaseConnections" \
  --namespace "AWS/RDS" \
  --statistic "Average" \
  --period 300 \
  --threshold 40 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions Name=DBInstanceIdentifier,Value="$DB_INSTANCE" \
  --evaluation-periods 1 \
  --alarm-actions "$SNS_TOPIC_ARN" \
  --ok-actions "$SNS_TOPIC_ARN" \
  --region "$REGION"

echo "Created RDS Connection Count alarm"

echo "====== CloudWatch Alarms Created ======"
echo "SNS Topic ARN: $SNS_TOPIC_ARN"
echo
echo "Remember to add subscriptions to the SNS topic to receive alarm notifications:"
echo "aws sns subscribe --topic-arn \"$SNS_TOPIC_ARN\" --protocol email --notification-endpoint alerts@example.com" 