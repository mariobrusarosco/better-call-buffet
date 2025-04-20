# Database Configuration

This document provides details about the RDS PostgreSQL setup for Better Call Buffet.

## RDS Instance Details

- **Instance Identifier**: bcb-db
- **Engine**: PostgreSQL 15.x
- **Instance Class**: db.t3.micro (1 vCPU, 1 GB RAM)
- **Storage**: 20 GB General Purpose SSD (gp2)
- **Endpoint**: ************.amazonaws.com
- **Port**: 5432
- **Database Name**: better_call_buffet

## Connection Information

Use the following connection string format in your application:

```
postgresql://username:password@************.amazonaws.com:5432/better_call_buffet
```

The actual connection string is stored securely in the `.env` file.

## Parameter Group Configuration

The database uses a custom parameter group with the following settings:

- **max_connections**: 50
- **shared_buffers**: 262144 KB (256 MB)
- **work_mem**: 4096 KB (4 MB)
- **log_min_duration_statement**: 1000 (1 second)

## Monitoring

CloudWatch alarms have been configured to monitor:

1. **CPU Utilization**: Alerts if > 80% for 10 minutes
2. **Free Storage Space**: Alerts if < 2 GB
3. **Database Connections**: Alerts if > 40 connections

Alerts are sent to the `BCB-Alerts` SNS topic, which delivers email notifications.

## Backup Configuration

- **Automated Backups**: Enabled with 7-day retention
- **Backup Window**: No preference (AWS-selected)
- **Maintenance Window**: No preference (AWS-selected)

## Security

- **VPC Security Group**: BCB-DB-SG
- **Public Accessibility**: No
- **Storage Encryption**: Enabled
- **Parameter Group**: bcb-postgres-params

## Connecting to the Database

### From Application Code

```python
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.environ.get("DATABASE_URL")

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)
```

### Using psql Command Line

```bash
psql -h ************.amazonaws.com -U postgres -d better_call_buffet
```

## Troubleshooting

If you encounter connection issues:

1. Check that the EC2 instance is in the correct security group
2. Verify that the security group allows PostgreSQL traffic (port 5432)
3. Ensure the database credentials are correct
4. Verify that the RDS instance is in the "Available" state 