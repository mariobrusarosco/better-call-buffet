# AWS RDS (Relational Database Service)

## What is RDS?

AWS RDS (Relational Database Service) is a managed database service that makes it easier to set up, operate, and scale a relational database in the cloud. Instead of managing database infrastructure yourself, AWS handles routine database tasks such as provisioning, backups, patching, and scaling.

Think of RDS as a **database-as-a-service** that provides:

- Automated administration tasks
- High availability options
- Scalable capacity
- Enhanced security features
- Performance optimization

## How RDS Works

```
                                    ┌─────────────────┐
                                    │                 │
                                    │ Your Application│
                                    │                 │
                                    └────────┬────────┘
                                             │
                                             ▼
┌────────────────────────────────────────────────────────────────────────┐
│                            AWS RDS                                     │
│                                                                        │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────┐ │
│  │  Database    │   │  Automated   │   │   Backups    │   │Monitoring│ │
│  │  Engine      │   │   Patching   │   │              │   │          │ │
│  └──────────────┘   └──────────────┘   └──────────────┘   └──────────┘ │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          AWS Resources                                  │
│                                                                         │
│    ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌─────┐  │
│    │ EC2    │  │ EBS    │  │ VPC    │  │ KMS    │  │ IAM    │  │ ... │  │
│    │(Hidden)│  │Volumes │  │Subnets │  │(Encrypt)│  │Roles  │  │     │  │
│    └────────┘  └────────┘  └────────┘  └────────┘  └────────┘  └─────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

When you create an RDS instance:

1. **Choose a database engine**: Select your preferred database (PostgreSQL, MySQL, etc.)
2. **Select instance configuration**: Choose size, storage, and network settings
3. **RDS handles the rest**:
   - Provisions underlying EC2 instances (hidden from you)
   - Creates and configures database
   - Sets up high availability (if selected)
   - Configures automated backups
   - Manages ongoing maintenance

## Key Components

1. **DB Instance**: The fundamental building block of Amazon RDS

   - Isolated database environment running in the cloud
   - Can contain multiple databases
   - Runs a specific database engine version

2. **DB Parameter Group**: Acts as a container for engine configuration values

   - Controls memory allocation
   - Query execution behavior
   - Logging settings
   - Connection limits

3. **DB Subnet Group**: Subnet collection where you can place your database

   - Spans multiple Availability Zones
   - Enables high availability
   - Controls network access

4. **Option Groups**: Additional features for specific database engines
   - Enable advanced database engine features
   - Example: Oracle Enterprise Manager

## Supported Database Engines

RDS supports several database engines:

- PostgreSQL
- MySQL
- MariaDB
- Oracle
- SQL Server
- Amazon Aurora (MySQL/PostgreSQL-compatible)

## Benefits for Better Call Buffet

For our Better Call Buffet application, RDS provides several key advantages:

1. **Reduced Administrative Burden**: No need to manage database infrastructure

2. **Automated Backups**: Daily automated backups with point-in-time recovery

3. **Easy Scaling**: Vertical scaling with minimal downtime

4. **Enhanced Security**: Network isolation, encryption, and IAM integration

5. **Monitoring**: Integrated CloudWatch metrics and Performance Insights

6. **Cost-Effective**: Free tier eligible for 12 months

## RDS Architecture for Better Call Buffet

We're implementing a simple single-instance RDS deployment initially:

```
                         VPC (10.0.0.0/16)
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  ┌───────────────────────────┐   ┌───────────────────────┐  │
│  │                           │   │                       │  │
│  │   Public Subnet 1a-DB     │   │  Public Subnet 1b-DB  │  │
│  │   10.0.11.0/24            │   │  10.0.12.0/24         │  │
│  │                           │   │                       │  │
│  │   ┌───────────────────┐   │   │                       │  │
│  │   │                   │   │   │                       │  │
│  │   │  RDS PostgreSQL   │   │   │                       │  │
│  │   │  db.t3.micro      │   │   │                       │  │
│  │   │                   │   │   │                       │  │
│  │   └───────────────────┘   │   │                       │  │
│  │                           │   │                       │  │
│  └───────────────────────────┘   └───────────────────────┘  │
│                                                             │
│               ▲                                             │
│               │                                             │
│  ┌────────────┴────────────┐   ┌───────────────────────┐   │
│  │                         │   │                       │   │
│  │   Public Subnet 1a      │   │   Public Subnet 1b    │   │
│  │   10.0.1.0/24           │   │   10.0.2.0/24         │   │
│  │                         │   │                       │   │
│  │   ┌─────────────────┐   │   │  ┌─────────────────┐  │   │
│  │   │                 │   │   │  │                 │  │   │
│  │   │ Elastic Beanstalk│   │   │  │ Elastic Beanstalk│  │   │
│  │   │ (Application)    │   │   │  │ (Application)    │  │   │
│  │   │                 │   │   │  │                 │  │   │
│  │   └─────────────────┘   │   │  └─────────────────┘  │   │
│  │                         │   │                       │   │
│  └─────────────────────────┘   └───────────────────────┘   │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

## RDS Security Layers

RDS employs multiple security layers:

```
┌───────────────────────────────────────────────────────────┐
│                      RDS Security Layers                  │
├───────────────────────────────────────────────────────────┤
│ Network Security                                          │
├───────────────────┬───────────────────┬───────────────────┤
│  VPC              │  Security Groups  │  Subnet Groups    │
│  Isolation        │  Port Control     │  Placement        │
├───────────────────┴───────────────────┴───────────────────┤
│ Authentication & Authorization                            │
├───────────────────┬───────────────────┬───────────────────┤
│  Database         │  IAM              │  Password         │
│  Authentication   │  Integration      │  Policies         │
├───────────────────┴───────────────────┴───────────────────┤
│ Encryption                                                │
├───────────────────┬───────────────────┬───────────────────┤
│  Encryption       │  Transport        │  Key              │
│  at Rest (KMS)    │  Layer Security   │  Management       │
└───────────────────┴───────────────────┴───────────────────┘
```

## Common RDS Operations

### Instance Maintenance

```
Maintenance Tasks:
├── Database Engine Upgrades
│   └── Minor vs Major Version Upgrades
│
├── Operating System Patches
│   └── Security Updates
│
└── Hardware Maintenance
    └── Host Replacement
```

### Backup and Recovery

```
Backup Options:
├── Automated Backups
│   ├── Daily Full Backup
│   ├── 5-minute Transaction Logs
│   └── Point-in-Time Recovery
│
└── Manual Snapshots
    ├── User-initiated
    ├── Persistent (even after instance deletion)
    └── Cross-region/account copy option
```

### Scaling Options

```
Scaling Methods:
├── Vertical Scaling (Instance Modification)
│   ├── Compute (CPU/Memory)
│   └── Storage (Size/IOPS)
│
└── Read Scaling
    └── Read Replicas
```

## Performance Monitoring

RDS provides multiple monitoring tools:

1. **CloudWatch Metrics**: Basic performance metrics

   - CPU Utilization
   - Database Connections
   - Storage Space
   - Free Memory

2. **Enhanced Monitoring**: More granular OS-level metrics

   - Process List
   - Memory Usage Details
   - Disk I/O Details

3. **Performance Insights**: Database performance analysis
   - Database Load
   - Top SQL Queries
   - Wait Events
   - Host/User Dimensions

## Common RDS Configurations

| Configuration    | Small Workload (Our Case) | Medium Workload | Large Workload |
| ---------------- | ------------------------- | --------------- | -------------- |
| Instance Type    | db.t3.micro               | db.m5.large     | db.r5.2xlarge  |
| vCPU             | 1                         | 2               | 8              |
| Memory           | 1 GB                      | 8 GB            | 64 GB          |
| Storage          | 20 GB                     | 100 GB          | 500+ GB        |
| Multi-AZ         | No                        | Yes             | Yes            |
| Read Replicas    | 0                         | 1-2             | 3+             |
| Backup Retention | 7 days                    | 14 days         | 30+ days       |

## Resources

- [AWS RDS Documentation](https://docs.aws.amazon.com/rds/index.html)
- [RDS Best Practices](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_BestPractices.html)
- [PostgreSQL on Amazon RDS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html)
