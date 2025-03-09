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
│  └──────────┬──────────────┘        └─────────────────────────┘ │
│             │                                                    │
│             ▼                                                    │
│        NAT Gateway                                               │
│             │                                                    │
│             ▼                                                    │
│  ┌─────────────────────────┐        ┌─────────────────────────┐ │
│  │                         │        │                         │ │
│  │  Private Subnet 1a      │        │  Private Subnet 1b      │ │
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

## Design Rationale

### 1. Multi-AZ Architecture

We're using two Availability Zones (AZs) for:

- **High Availability**: Protection against AZ failures
- **Disaster Recovery**: Ability to recover if one AZ goes down
- **Load Distribution**: Spread traffic across multiple AZs

### 2. Public vs Private Subnets

**Public Subnets**:
- Host internet-facing resources (application servers)
- Have direct route to Internet Gateway
- Resources receive public IPs

**Private Subnets**:
- Host sensitive resources (databases)
- No direct internet access
- Outbound internet access through NAT Gateway only
- Enhanced security for data tier

### 3. CIDR Block Allocation

```
VPC CIDR: 10.0.0.0/16 (65,536 IP addresses)

Subnet Allocation:
├── Public Subnets
│   ├── 10.0.1.0/24 (256 IPs in AZ 1a)
│   └── 10.0.2.0/24 (256 IPs in AZ 1b)
│
└── Private Subnets
    ├── 10.0.11.0/24 (256 IPs in AZ 1a)
    └── 10.0.12.0/24 (256 IPs in AZ 1b)
```

This allocation:
- Provides room for growth
- Maintains clear separation between public/private
- Follows AWS best practices for subnet sizing

### 4. NAT Gateway Design

We're using a single NAT Gateway in one public subnet to:
- Allow private resources to access the internet
- Reduce costs (single NAT vs multiple NATs)
- Provide sufficient reliability for our needs

**Note**: For production environments with stricter high-availability requirements, you might want a NAT Gateway in each AZ.

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
├── NAT Gateway: ~$32/month
│   └── Cost-saving option: Schedule on/off for dev
├── Internet Gateway: Free
└── VPC/Subnets: Free
```

## Implementation Sequence

1. Create VPC with DNS hostnames enabled
2. Create all 4 subnets across 2 AZs
3. Create and attach Internet Gateway
4. Create NAT Gateway in public subnet
5. Create and configure route tables
6. Associate subnets with appropriate route tables
7. Create security groups

## Security Considerations

- Private subnets have no direct internet access
- Database only accessible from application tier
- All traffic between subnets is logged (VPC Flow Logs)
- Security groups follow principle of least privilege

## Future Expansion

This design allows for:
- Adding more application servers
- Implementing load balancers
- Adding additional database replicas
- Expanding to additional AZs if needed 