# Decision Record: RDS Configuration Choices (DR-003)

## Status
Accepted (March 9, 2023)

## Context
The Better Call Buffet application requires a relational database to store user data, financial information, and other application resources. We need to determine the appropriate database architecture, instance type, storage, and configuration settings to balance:

1. Performance needs for a financial application
2. Budget constraints ($25/month total infrastructure)
3. Development vs. production requirements
4. Security considerations
5. Operational overhead

## Decision
We have decided to implement a single-instance RDS PostgreSQL deployment with the following configuration:

### Instance Configuration
- **Engine**: PostgreSQL 15.x (latest available version)
- **Instance Type**: db.t3.micro (1 vCPU, 1 GB RAM)
- **Storage**: 20 GB General Purpose SSD (gp2)
- **Multi-AZ**: No (single availability zone deployment)
- **Public Access**: No (only accessible from within VPC)

### Database Configuration
- **Parameter Group**: Custom with optimized settings:
  - `max_connections`: 50
  - `shared_buffers`: 256MB
  - `work_mem`: 4MB
  - `log_min_duration_statement`: 1000 (1 second)

### Security Configuration
- **Network**: Placed in database-specific subnets
- **Security Group**: Access limited to application servers only
- **Encryption**: Enable encryption at rest
- **Authentication**: Password authentication

### Backup Configuration
- **Automated Backups**: Enabled with 7-day retention
- **Backup Window**: Off-peak hours
- **Snapshot Strategy**: Weekly manual snapshots

## Alternatives Considered

### Aurora Serverless
- **Pros**: Pay-per-use, automatic scaling, can go to zero when not used
- **Cons**: More expensive for continuous workloads, less predictable costs
- **Why Rejected**: Cost efficiency for our continuous workload pattern

### Multi-AZ Deployment
- **Pros**: Higher availability, automatic failover
- **Cons**: Doubles the cost, more than needed for development
- **Why Rejected**: Budget constraints, development-stage needs

### Larger Instance Types
- **Pros**: More CPU/memory for better performance
- **Cons**: Higher cost, overprovisioned for initial workload
- **Why Rejected**: Free tier eligible option sufficient for early usage

## Consequences

### Positive
- Stays within budget constraints
- Free tier eligible for first 12 months
- Sufficient performance for development and early production
- Automated backups for data protection
- Simplified management with AWS handling maintenance

### Negative
- Single point of failure (no high availability)
- Limited vertical scaling due to instance type
- May require migration as application scales
- Public subnet placement (due to NAT Gateway omission)

### Mitigations
- Implement robust backup strategy
- Document database migration process for future scaling
- Strict security group rules to compensate for public subnet placement
- Monitor performance metrics closely to anticipate scaling needs

## Implementation Plan
1. Create parameter group with optimized settings
2. Launch RDS instance in database subnet
3. Configure backup settings
4. Set up monitoring and alerts
5. Document connection information
6. Update application environment variables

## Related Documents
- [Phase 2 Implementation Plan](../phase2-planning.md)
- [RDS Explained](../rds-explained.md)
- [NAT Gateway Omission Decision](001-nat-gateway-omission.md)

## Notes
This decision should be revisited when:
- Free tier eligibility expires (12 months)
- Database performance metrics indicate scaling needs
- Application enters production use with real users
- Budget constraints change 