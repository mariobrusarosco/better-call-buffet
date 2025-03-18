# Phase 2: Database Infrastructure

## Overview

Phase 2 focuses on setting up the database infrastructure for Better Call Buffet. We'll create and configure an RDS PostgreSQL instance, set up backups, and ensure proper monitoring.

## Goals

1. ✅ Deploy a PostgreSQL database using AWS RDS
2. ✅ Establish appropriate database parameters and configuration
3. ✅ Implement backup and recovery procedures
4. ✅ Set up monitoring and alerting
5. ✅ Document database access patterns

## Prerequisites

- ✅ Completed VPC setup from Phase 1
- ✅ Database security group created
- ✅ RDS IAM role established

## Implementation Plan

### 1. RDS PostgreSQL Instance ✅

```bash
AWS Console → RDS → Create database:

1. Engine Options
   ├── Engine type: PostgreSQL
   ├── Version: 15.x (latest available)
   └── Templates: Free tier

2. Settings
   ├── DB instance identifier: bcb-db
   ├── Credentials: Set master username/password
   └── DB instance class: db.t3.micro (Free tier eligible)

3. Storage
   ├── Storage type: General Purpose SSD (gp2)
   ├── Allocated storage: 20 GB
   └── Storage autoscaling: Disable (for cost control)

4. Connectivity
   ├── VPC: BCB-Production-VPC
   ├── Subnet group: Create new (both db subnets)
   ├── Public access: No
   └── Security group: BCB-DB-SG (created in Phase 1)

5. Additional configuration
   ├── Initial database name: better_call_buffet
   ├── Backup retention: 7 days
   ├── Monitoring: Enhanced monitoring (Disable)
   └── Maintenance: Enable auto minor version upgrade
```

### 2. Database Parameter Group ✅

```bash
1. Create Parameter Group
   ├── Name: bcb-postgres-params
   ├── Description: BCB PostgreSQL parameters
   └── Family: postgres15

2. Configure Parameters
   ├── max_connections: 50
   ├── shared_buffers: 262144 KB (256 MB)
   ├── work_mem: 4096 KB (4 MB)
   └── log_min_duration_statement: 1000 (1 second)
```

### 3. Database Backup and Recovery ✅

```bash
Configure Automated Backups:
├── Backup window: Set to off-peak hours
├── Backup retention: 7 days
└── Enable automated snapshots: Yes

Manual Snapshot Procedure:
├── Schedule weekly manual snapshots
├── Retain monthly snapshots for 6 months
└── Document snapshot access procedure
```

### 4. Monitoring Setup ✅

```bash
1. CloudWatch Alarms
   ├── CPU Utilization > 80% for 5 minutes
   ├── Free Storage Space < 2GB
   ├── Database Connections > 40
   └── FreeableMemory < 256MB

2. Performance Insights
   ├── Enable Basic monitoring
   ├── Set retention to 7 days (free tier)
   └── Create dashboard for key metrics
```

### 5. Security Configuration ✅

```bash
1. Database Configuration
   ├── SSL: Enable
   ├── Database authentication: Password authentication
   └── Database port: 5432 (standard)

2. Database Connection String
   ├── Create structure: postgresql://username:password@endpoint:port/dbname
   ├── Store securely in environment variables
   └── Document access patterns for application
```

## Cost Analysis

```
Estimated Monthly Costs:
├── RDS db.t3.micro: ~$12-15/month
│   └── Free tier eligible for 12 months
├── Storage (20GB): Included in free tier
├── Backup storage: Included in free tier
└── Data transfer: Minimal (within same AZ)

Total: ~$0/month (during free tier)
       ~$15/month (post free tier)
```

## Decision Points

1. **Multi-AZ Deployment**
   - Initially: No (cost savings)
   - Future consideration: Yes for production

2. **Storage Type**
   - Initially: General Purpose SSD (gp2)
   - Alternative: Provisioned IOPS (io1) for higher performance

3. **Instance Sizing**
   - Initially: db.t3.micro (free tier, 1vCPU, 1GB RAM)
   - Upgrade path: db.t3.small (2GB RAM) when needed

## Testing Plan

1. ✅ Database Connection Tests
2. ✅ Basic CRUD Operations
3. 🔄 Performance Testing
4. 🔄 Backup and Restore Testing
5. ✅ Security Verification

## Documentation Requirements

1. ✅ Connection Information
2. ✅ Backup/Restore Procedures
3. ✅ Monitoring Dashboard Guide
4. ✅ Security Best Practices
5. 🔄 Performance Tuning Guide

## Next Steps Checklist

- [x] Create RDS parameter group
- [x] Launch PostgreSQL RDS instance
- [x] Configure backup settings
- [x] Set up monitoring alarms
- [x] Test database connectivity
- [x] Document connection information
- [x] Update application environment variables
- [x] Initialize database schema

## Phase 2 Complete! ✅

Phase 2 of the Better Call Buffet infrastructure is now complete. We have successfully:

1. **Set up the RDS PostgreSQL instance**: A db.t3.micro instance with PostgreSQL 15.x
2. **Configured parameter groups**: Optimized for our application needs
3. **Established monitoring**: CloudWatch alarms for CPU, storage, and connections
4. **Created documentation**: Detailed database configuration and access patterns
5. **Initialized the schema**: Created database tables for the application
6. **Tested connectivity**: Verified application can connect to the database

Our next phase will focus on setting up the application infrastructure using Elastic Beanstalk. 