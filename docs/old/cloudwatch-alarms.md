# CloudWatch Alarms for Elastic Beanstalk Application

This document outlines recommended CloudWatch alarms for monitoring the Better Call Buffet application deployed on AWS Elastic Beanstalk.

## Infrastructure Alarms

### Elastic Beanstalk Environment Health

Monitors the overall health of the Elastic Beanstalk environment.

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "BCB-Prod-EnvironmentHealth" \
  --alarm-description "Alarm when environment health is not Green" \
  --metric-name "EnvironmentHealth" \
  --namespace "AWS/ElasticBeanstalk" \
  --statistic "Average" \
  --period 300 \
  --threshold 40 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions Name=EnvironmentName,Value=better-call-buffet-prod \
  --evaluation-periods 1 \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:BCB-Alerts" \
  --ok-actions "arn:aws:sns:us-east-1:123456789012:BCB-Alerts"
```

### CPU Utilization

Alerts when instance CPU usage is too high, indicating potential scaling needs.

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "BCB-Prod-HighCPUUtilization" \
  --alarm-description "Alarm when CPU exceeds 70% for 5 minutes" \
  --metric-name "CPUUtilization" \
  --namespace "AWS/EC2" \
  --statistic "Average" \
  --period 300 \
  --threshold 70 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions Name=AutoScalingGroupName,Value=better-call-buffet-prod-asg \
  --evaluation-periods 1 \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:BCB-Alerts" \
  --ok-actions "arn:aws:sns:us-east-1:123456789012:BCB-Alerts"
```

### Memory Utilization

Monitors memory usage on instances.

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "BCB-Prod-HighMemoryUtilization" \
  --alarm-description "Alarm when Memory exceeds 80% for 5 minutes" \
  --metric-name "MemoryUtilization" \
  --namespace "AWS/ElasticBeanstalk" \
  --statistic "Average" \
  --period 300 \
  --threshold 80 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions Name=EnvironmentName,Value=better-call-buffet-prod \
  --evaluation-periods 1 \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:BCB-Alerts" \
  --ok-actions "arn:aws:sns:us-east-1:123456789012:BCB-Alerts"
```

## Application Performance Alarms

### 5XX Error Rate

Alerts when the application is returning a high rate of server errors.

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "BCB-Prod-High5XXErrors" \
  --alarm-description "Alarm when 5XX errors exceed 10 per minute" \
  --metric-name "HTTPCode_Target_5XX_Count" \
  --namespace "AWS/ApplicationELB" \
  --statistic "Sum" \
  --period 60 \
  --threshold 10 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions Name=LoadBalancer,Value=better-call-buffet-prod-alb \
  --evaluation-periods 1 \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:BCB-Alerts" \
  --ok-actions "arn:aws:sns:us-east-1:123456789012:BCB-Alerts"
```

### Response Time

Monitors application response time to detect performance issues.

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "BCB-Prod-HighResponseTime" \
  --alarm-description "Alarm when response time exceeds 2 seconds" \
  --metric-name "TargetResponseTime" \
  --namespace "AWS/ApplicationELB" \
  --statistic "Average" \
  --period 300 \
  --threshold 2 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions Name=LoadBalancer,Value=better-call-buffet-prod-alb \
  --evaluation-periods 1 \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:BCB-Alerts" \
  --ok-actions "arn:aws:sns:us-east-1:123456789012:BCB-Alerts"
```

### Request Count

Monitors for unexpected increases or decreases in traffic.

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "BCB-Prod-LowRequestCount" \
  --alarm-description "Alarm when request count is too low (potential outage)" \
  --metric-name "RequestCount" \
  --namespace "AWS/ApplicationELB" \
  --statistic "Sum" \
  --period 300 \
  --threshold 10 \
  --comparison-operator "LessThanThreshold" \
  --dimensions Name=LoadBalancer,Value=better-call-buffet-prod-alb \
  --evaluation-periods 3 \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:BCB-Alerts" \
  --ok-actions "arn:aws:sns:us-east-1:123456789012:BCB-Alerts"
```

## Database Alarms

### RDS CPU Utilization

Alerts when the database CPU usage is high.

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "BCB-DB-HighCPUUtilization" \
  --alarm-description "Alarm when RDS CPU exceeds 80% for 5 minutes" \
  --metric-name "CPUUtilization" \
  --namespace "AWS/RDS" \
  --statistic "Average" \
  --period 300 \
  --threshold 80 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions Name=DBInstanceIdentifier,Value=bcb-db \
  --evaluation-periods 1 \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:BCB-Alerts" \
  --ok-actions "arn:aws:sns:us-east-1:123456789012:BCB-Alerts"
```

### RDS Free Storage Space

Monitors available storage in the database.

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "BCB-DB-LowFreeStorageSpace" \
  --alarm-description "Alarm when free storage space is below 10GB" \
  --metric-name "FreeStorageSpace" \
  --namespace "AWS/RDS" \
  --statistic "Average" \
  --period 300 \
  --threshold 10000000000 \
  --comparison-operator "LessThanThreshold" \
  --dimensions Name=DBInstanceIdentifier,Value=bcb-db \
  --evaluation-periods 1 \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:BCB-Alerts" \
  --ok-actions "arn:aws:sns:us-east-1:123456789012:BCB-Alerts"
```

### RDS Connection Count

Alerts when too many database connections are occurring.

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "BCB-DB-HighConnectionCount" \
  --alarm-description "Alarm when database connections exceed 80% of maximum" \
  --metric-name "DatabaseConnections" \
  --namespace "AWS/RDS" \
  --statistic "Average" \
  --period 300 \
  --threshold 40 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions Name=DBInstanceIdentifier,Value=bcb-db \
  --evaluation-periods 1 \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:BCB-Alerts" \
  --ok-actions "arn:aws:sns:us-east-1:123456789012:BCB-Alerts"
```

## Setting Up Alarms

You can set up these alarms using one of the following methods:

### Using AWS Console

1. Navigate to CloudWatch in the AWS Console
2. Select "Alarms" from the left menu
3. Click "Create alarm"
4. Follow the wizard to set up each alarm

### Using AWS CLI

Run each of the commands above, replacing the SNS topic ARN with your own:

```bash
# Example: Update the ARN for your SNS topic
TOPIC_ARN=$(aws sns list-topics --query 'Topics[?contains(TopicArn, `BCB-Alerts`)].TopicArn' --output text)

# Update the command with your ARN
aws cloudwatch put-metric-alarm \
  --alarm-name "BCB-Prod-EnvironmentHealth" \
  # ... other parameters ...
  --alarm-actions "$TOPIC_ARN" \
  --ok-actions "$TOPIC_ARN"
```

### Using CloudFormation

Consider creating a CloudFormation template to manage all alarms as code.

## Best Practices

1. **Start small**: Begin with essential alarms and add more as needed
2. **Tune thresholds**: Adjust thresholds based on observed patterns
3. **Reduce noise**: Avoid setting alarms too sensitive to avoid alert fatigue
4. **Document responses**: Create runbooks for each alarm type
5. **Test alerts**: Periodically verify alarms work by triggering test conditions 