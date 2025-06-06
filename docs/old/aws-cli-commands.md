# AWS CLI Commands Reference

This document provides a reference for AWS CLI commands used in the Better Call Buffet project, particularly for RDS database setup and monitoring.

## Getting Started with AWS CLI

### Installation

```bash
# Linux
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Verify installation
aws --version
```

### Configuration

```bash
# Basic configuration
aws configure

# You'll be prompted for:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region name (e.g., us-east-1)
# - Default output format (json recommended)
```

### Checking Configuration

```bash
# Verify identity
aws sts get-caller-identity

# List configured profiles
aws configure list-profiles

# View configuration
aws configure list
```

## CloudWatch Commands

### Creating Alarms

```bash
# Basic alarm syntax
aws cloudwatch put-metric-alarm \
    --alarm-name "AlarmName" \
    --alarm-description "Description" \
    --metric-name "MetricName" \
    --namespace "Namespace" \
    --statistic Average \
    --period 300 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=DimensionName,Value=DimensionValue \
    --evaluation-periods 2 \
    --alarm-actions arn:aws:sns:region:account-id:topic-name

# CPU Utilization Alarm for RDS
aws cloudwatch put-metric-alarm \
    --alarm-name "BCB-DB-HighCPU" \
    --alarm-description "Alarm when CPU exceeds 80% for 5 minutes" \
    --metric-name "CPUUtilization" \
    --namespace "AWS/RDS" \
    --statistic Average \
    --period 300 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=DBInstanceIdentifier,Value=bcb-db \
    --evaluation-periods 2 \
    --alarm-actions arn:aws:sns:us-east-1:905418297381:BCB-Alerts

# Free Storage Space Alarm for RDS
aws cloudwatch put-metric-alarm \
    --alarm-name "BCB-DB-LowStorage" \
    --alarm-description "Alarm when free storage drops below 2GB" \
    --metric-name "FreeStorageSpace" \
    --namespace "AWS/RDS" \
    --statistic Average \
    --period 300 \
    --threshold 2000000000 \
    --comparison-operator LessThanThreshold \
    --dimensions Name=DBInstanceIdentifier,Value=bcb-db \
    --evaluation-periods 2 \
    --alarm-actions arn:aws:sns:us-east-1:905418297381:BCB-Alerts

# Database Connections Alarm
aws cloudwatch put-metric-alarm \
    --alarm-name "BCB-DB-HighConnections" \
    --alarm-description "Alarm when connections exceed 40" \
    --metric-name "DatabaseConnections" \
    --namespace "AWS/RDS" \
    --statistic Maximum \
    --period 300 \
    --threshold 40 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=DBInstanceIdentifier,Value=bcb-db \
    --evaluation-periods 2 \
    --alarm-actions arn:aws:sns:us-east-1:905418297381:BCB-Alerts
```

### Creating Dashboards

```bash
# Basic dashboard syntax
aws cloudwatch put-dashboard \
    --dashboard-name 'DashboardName' \
    --dashboard-body '{"widgets":[...]}'

# RDS Monitoring Dashboard
aws cloudwatch put-dashboard \
    --dashboard-name 'BCB-RDS-Dashboard' \
    --dashboard-body '{
        "widgets":[
            {
                "type":"metric",
                "x":0,
                "y":0,
                "width":12,
                "height":6,
                "properties":{
                    "metrics":[
                        ["AWS/RDS","CPUUtilization","DBInstanceIdentifier","bcb-db",{"region":"us-east-1"}]
                    ],
                    "view":"timeSeries",
                    "stacked":false,
                    "region":"us-east-1",
                    "title":"CPU Utilization",
                    "period":300,
                    "stat":"Average"
                }
            },
            {
                "type":"metric",
                "x":12,
                "y":0,
                "width":12,
                "height":6,
                "properties":{
                    "metrics":[
                        ["AWS/RDS","FreeStorageSpace","DBInstanceIdentifier","bcb-db",{"region":"us-east-1"}]
                    ],
                    "view":"timeSeries",
                    "stacked":false,
                    "region":"us-east-1",
                    "title":"Free Storage Space",
                    "period":300,
                    "stat":"Average"
                }
            },
            {
                "type":"metric",
                "x":0,
                "y":6,
                "width":12,
                "height":6,
                "properties":{
                    "metrics":[
                        ["AWS/RDS","DatabaseConnections","DBInstanceIdentifier","bcb-db",{"region":"us-east-1"}]
                    ],
                    "view":"timeSeries",
                    "stacked":false,
                    "region":"us-east-1",
                    "title":"Database Connections",
                    "period":300,
                    "stat":"Average"
                }
            },
            {
                "type":"metric",
                "x":12,
                "y":6,
                "width":12,
                "height":6,
                "properties":{
                    "metrics":[
                        ["AWS/RDS","ReadIOPS","DBInstanceIdentifier","bcb-db",{"region":"us-east-1"}],
                        ["AWS/RDS","WriteIOPS","DBInstanceIdentifier","bcb-db",{"region":"us-east-1"}]
                    ],
                    "view":"timeSeries",
                    "stacked":false,
                    "region":"us-east-1",
                    "title":"Read/Write IOPS",
                    "period":300,
                    "stat":"Average"
                }
            }
        ]
    }'
```

### Viewing Alarms and Metrics

```bash
# List all CloudWatch alarms
aws cloudwatch describe-alarms

# List all alarms for a specific prefix
aws cloudwatch describe-alarms --alarm-name-prefix BCB-DB

# Get metrics for RDS
aws cloudwatch list-metrics --namespace AWS/RDS

# Get metrics for a specific instance
aws cloudwatch list-metrics --namespace AWS/RDS --dimensions Name=DBInstanceIdentifier,Value=bcb-db
```

## SNS Commands

### Creating Topics

```bash
# Create an SNS topic
aws sns create-topic --name TopicName

# For our alerts
aws sns create-topic --name BCB-Alerts
# Output: {"TopicArn":"arn:aws:sns:us-east-1:905418297381:BCB-Alerts"}
```

### Managing Subscriptions

```bash
# Subscribe an email to a topic
aws sns subscribe \
    --topic-arn arn:aws:sns:region:account-id:topic-name \
    --protocol email \
    --notification-endpoint email@example.com

# For our alerts
aws sns subscribe \
    --topic-arn arn:aws:sns:us-east-1:905418297381:BCB-Alerts \
    --protocol email \
    --notification-endpoint your-email@example.com
```

### Listing Topics and Subscriptions

```bash
# List all SNS topics
aws sns list-topics

# List subscriptions for a topic
aws sns list-subscriptions-by-topic --topic-arn arn:aws:sns:us-east-1:905418297381:BCB-Alerts
```

## RDS Commands

### Describing Instances

```bash
# List all RDS instances
aws rds describe-db-instances

# Describe a specific instance
aws rds describe-db-instances --db-instance-identifier bcb-db
```

### Parameter Groups

```bash
# Create a parameter group
aws rds create-db-parameter-group \
    --db-parameter-group-name bcb-postgres-params \
    --db-parameter-group-family postgres15 \
    --description "Better Call Buffet PostgreSQL parameters"

# Modify parameters
aws rds modify-db-parameter-group \
    --db-parameter-group-name bcb-postgres-params \
    --parameters "ParameterName=max_connections,ParameterValue=50,ApplyMethod=immediate" \
                 "ParameterName=shared_buffers,ParameterValue=262144,ApplyMethod=pending-reboot" \
                 "ParameterName=work_mem,ParameterValue=4096,ApplyMethod=immediate" \
                 "ParameterName=log_min_duration_statement,ParameterValue=1000,ApplyMethod=immediate"

# List parameters in a group
aws rds describe-db-parameters --db-parameter-group-name bcb-postgres-params
```

### Snapshots

```bash
# Create a manual snapshot
aws rds create-db-snapshot \
    --db-instance-identifier bcb-db \
    --db-snapshot-identifier bcb-db-snapshot-manual-1

# List all snapshots
aws rds describe-db-snapshots

# List snapshots for a specific instance
aws rds describe-db-snapshots --db-instance-identifier bcb-db
```

## Understanding Key Parameters

### CloudWatch Alarms

- **alarm-name**: Unique identifier for the alarm
- **metric-name**: The metric being monitored (e.g., CPUUtilization)
- **namespace**: The AWS service namespace (e.g., AWS/RDS)
- **statistic**: How to aggregate data points (Average, Maximum, Minimum, Sum, SampleCount)
- **period**: The length of time to evaluate the metric in seconds (e.g., 300 = 5 minutes)
- **threshold**: The value to compare against
- **comparison-operator**: How to compare the metric to the threshold (GreaterThanThreshold, LessThanThreshold, etc.)
- **dimensions**: Identifies the resources for the metric (e.g., DBInstanceIdentifier=bcb-db)
- **evaluation-periods**: The number of consecutive periods the metric must be in alarm state
- **alarm-actions**: The ARN of the action to take when the alarm state is triggered

### CloudWatch Dashboards

- **dashboard-name**: Unique identifier for the dashboard
- **dashboard-body**: JSON document describing the dashboard widgets
  - **type**: Widget type (metric, text, alarm, etc.)
  - **x, y**: Position coordinates
  - **width, height**: Widget dimensions
  - **properties.metrics**: Array of metrics to display
  - **properties.view**: Visualization type (timeSeries, singleValue, etc.)
  - **properties.region**: AWS region
  - **properties.title**: Widget title

## Best Practices

1. **Use profiles for different environments**:
   ```bash
   aws configure --profile production
   aws --profile production cloudwatch describe-alarms
   ```

2. **Script common operations**:
   Create shell scripts for frequently used commands.

3. **Use parameter files for complex JSON**:
   ```bash
   aws cloudwatch put-dashboard --dashboard-name 'BCB-RDS-Dashboard' --dashboard-body file://dashboard.json
   ```

4. **Set default output format**:
   ```bash
   aws configure set output json
   ```

5. **Filter outputs with JQ**:
   ```bash
   aws rds describe-db-instances --query 'DBInstances[].Endpoint.Address' --output json | jq .
   ```

## Troubleshooting

### Common Issues

1. **Credentials Error**:
   ```
   Unable to locate credentials. You can configure credentials by running "aws configure".
   ```
   Solution: Run `aws configure` with valid credentials.

2. **Region Error**:
   ```
   You must specify a region. You can also configure your region by running "aws configure".
   ```
   Solution: Specify the region with `--region` or set a default with `aws configure`.

3. **Permission Denied**:
   ```
   An error occurred (AccessDenied) when calling the [Operation]: User: [ARN] is not authorized to perform: [Action]
   ```
   Solution: Ensure your IAM user/role has the necessary permissions.

### Getting Help

```bash
# General AWS CLI help
aws help

# Help for a specific service
aws cloudwatch help

# Help for a specific command
aws cloudwatch put-metric-alarm help
``` 