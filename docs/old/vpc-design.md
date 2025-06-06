# VPC Design for Better Call Buffet

## Architecture Overview

```
                                  Internet
                                     │
                                     ▼
                                  Internet
                                   Gateway
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  VPC (10.0.0.0/16)                                              │
│                                                                 │
│  ┌─────────────────────────┐        ┌─────────────────────────┐ │
│  │                         │        │                         │ │
│  │  Public Subnet 1a       │        │  Public Subnet 1b       │ │
│  │  10.0.1.0/24            │        │  10.0.2.0/24            │ │
│  │                         │        │                         │ │
│  │  ┌─────────────────┐    │        │  ┌─────────────────┐    │ │
│  │  │                 │    │        │  │                 │    │ │
│  │  │  EC2 Instance   │    │        │  │  EC2 Instance   │    │ │
│  │  │  (Application)  │    │        │  │  (Application)  │    │ │
│  │  │                 │    │        │  │                 │    │ │
│  │  └─────────────────┘    │        │  └─────────────────┘    │ │
│  │                         │        │                         │ │
│  └─────────────────────────┘        └─────────────────────────┘ │
│                                                                 │
│  ┌─────────────────────────┐        ┌─────────────────────────┐ │
│  │                         │        │                         │ │
│  │  Public Subnet 1a-DB    │        │  Public Subnet 1b-DB    │ │
│  │  10.0.11.0/24           │        │  10.0.12.0/24           │ │
│  │                         │        │                         │ │
│  │  ┌─────────────────┐    │        │  ┌─────────────────┐    │ │
│  │  │                 │    │        │  │                 │    │ │
│  │  │  RDS Instance   │◄───┼────────┼──►  RDS Standby    │    │ │
│  │  │  (Database)     │    │        │  │  (Optional)     │    │ │
│  │  │                 │    │        │  │                 │    │ │
│  │  └─────────────────┘    │        │  └─────────────────┘    │ │
│  │                         │        │                         │ │
│  └─────────────────────────┘        └─────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Budget Decision Log

### NAT Gateway Omission

**Decision**: We've decided to omit the NAT Gateway from our initial architecture.

**Rationale**:
- NAT Gateway costs approximately $32/month
- Our monthly budget is capped at $25
- Initial development can proceed without strict network isolation

**Implications**:
- All subnets will be public subnets with direct internet access
- Database will use security groups for protection rather than network isolation
- We will use naming convention "Public Subnet 1a-DB" to indicate future migration plans
- We can add NAT Gateway and convert to private subnets in the future

**Future Plans**:
- Add NAT Gateway when budget allows
- Convert database subnets to private once NAT Gateway is in place
- Document this as a "development" architecture pattern

## Design Rationale

### 1. Multi-AZ Architecture

We're using two Availability Zones (AZs) for:

- **High Availability**: Protection against AZ failures
- **Disaster Recovery**: Ability to recover if one AZ goes down
- **Load Distribution**: Spread traffic across multiple AZs

### 2. All Public Subnets (Budget-Constrained Design)

Due to budget constraints, we're using all public subnets:
- All subnets have direct route to Internet Gateway
- Resources use security groups for protection
- Naming convention preserves intended architecture
- Future migration path to public/private is preserved

### 3. CIDR Block Allocation

```
VPC CIDR: 10.0.0.0/16 (65,536 IP addresses)

Subnet Allocation:
├── Application Subnets
│   ├── 10.0.1.0/24 (256 IPs in AZ 1a)
│   └── 10.0.2.0/24 (256 IPs in AZ 1b)
│
└── Database Subnets (Currently Public)
    ├── 10.0.11.0/24 (256 IPs in AZ 1a)
    └── 10.0.12.0/24 (256 IPs in AZ 1b)
```

This allocation:
- Provides room for growth
- Maintains clear separation between app/database
- Follows AWS best practices for subnet sizing
- Allows future conversion to private subnets

### 4. Security Compensation

Without network isolation via private subnets, we'll compensate with:
- Stricter security groups on database resources
- Limited access via security group source restrictions
- Potential use of AWS Secrets Manager
- Regular security audits

### 5. Security Groups

**Application Security Group**:
- Allows HTTP/HTTPS from anywhere
- Enables web traffic to application tier

**Database Security Group**:
- Allows PostgreSQL (5432) only from Application SG
- Restricts direct access to database
- Implements principle of least privilege

## Cost Considerations

```
Monthly Cost Estimates:
├── Internet Gateway: Free
├── VPC/Subnets: Free
└── NAT Gateway: Omitted ($0 instead of $32/month)

Total: $0/month for networking infrastructure
```

## Implementation Sequence

1. Create VPC with DNS hostnames enabled
2. Create all 4 subnets across 2 AZs
3. Create and attach Internet Gateway
4. Create and configure route tables
5. Associate subnets with appropriate route tables
6. Create security groups

## Security Considerations

- All subnets have direct internet access
- Database protected exclusively by security groups
- All traffic between subnets is logged (VPC Flow Logs)
- Security groups follow principle of least privilege

## Future Expansion

This design allows for:
- Adding NAT Gateway when budget permits
- Converting database subnets to private
- Adding more application servers
- Implementing load balancers 