# Phase 1: Foundation Implementation

## Cost Controls Setup

### 1. Create Budget Alerts
```bash
AWS Console → Billing Dashboard → Budgets:

1. Create budget
   ├── Name: "BCB-Monthly-Budget"
   ├── Period: Monthly
   ├── Budget amount: $25
   └── Start date: First day of next month

2. Set Alert Thresholds
   ├── First Alert: 50% ($12.50)
   ├── Second Alert: 80% ($20.00)
   └── Final Alert: 100% ($25.00)

3. Configure Notifications
   ├── Email subscribers: [Your email]
   └── Alert frequency: Daily
```

### 2. CloudWatch Billing Alarm
```bash
AWS Console → CloudWatch → Alarms:

1. Create Billing Alarm
   ├── Metric: Billing → Total Estimated Charge
   ├── Threshold: Static
   ├── Condition: Greater than $20
   └── Period: 6 hours

2. Configure Actions
   ├── Alarm state trigger: In alarm
   ├── SNS topic: Create new
   └── Topic name: "BCB-Billing-Alerts"
```

### 3. Daily Cost Monitoring
```bash
AWS Console → CloudWatch → Dashboards:

1. Create Dashboard
   ├── Name: "BCB-Cost-Monitoring"
   └── Add widgets for:
       ├── Daily spending
       ├── Service breakdown
       └── EC2 & RDS monitoring
```

## VPC Setup

### 1. VPC Configuration
```bash
AWS Console → VPC:

1. Create VPC
   ├── Name: "BCB-Production-VPC"
   ├── CIDR: 10.0.0.0/16
   └── Enable DNS hostnames

2. Create Subnets
   ├── Public Subnets
   │   ├── bcb-public-1a: 10.0.1.0/24 (AZ: us-east-1a)
   │   └── bcb-public-1b: 10.0.2.0/24 (AZ: us-east-1b)
   │
   └── Private Subnets
       ├── bcb-private-1a: 10.0.11.0/24 (AZ: us-east-1a)
       └── bcb-private-1b: 10.0.12.0/24 (AZ: us-east-1b)
```

### 2. Internet Connectivity
```bash
1. Internet Gateway
   ├── Create: "BCB-IGW"
   └── Attach to VPC

2. NAT Gateway (Cost-optimized)
   ├── Create: "BCB-NAT"
   ├── Subnet: bcb-public-1a
   └── Allocate Elastic IP

3. Route Tables
   ├── Public Route Table
   │   ├── Name: "BCB-Public-RT"
   │   └── Routes:
   │       ├── 10.0.0.0/16 → local
   │       └── 0.0.0.0/0 → Internet Gateway
   │
   └── Private Route Table
       ├── Name: "BCB-Private-RT"
       └── Routes:
           ├── 10.0.0.0/16 → local
           └── 0.0.0.0/0 → NAT Gateway
```

### 3. Security Groups
```bash
1. Application Security Group
   ├── Name: "BCB-App-SG"
   ├── Inbound Rules:
   │   ├── HTTP (80) from anywhere
   │   └── HTTPS (443) from anywhere
   └── Outbound Rules:
       └── All traffic to anywhere

2. Database Security Group
   ├── Name: "BCB-DB-SG"
   ├── Inbound Rules:
   │   └── PostgreSQL (5432) from BCB-App-SG
   └── Outbound Rules:
       └── All traffic to anywhere
```

## IAM Configuration

### 1. Service Roles
```bash
1. Elastic Beanstalk Role
   ├── Name: "BCB-EB-Role"
   └── Policies:
       ├── AWSElasticBeanstalkWebTier
       └── AWSElasticBeanstalkWorkerTier

2. RDS Role
   ├── Name: "BCB-RDS-Role"
   └── Policies:
       └── AmazonRDSFullAccess
```

### 2. User Policies
```bash
1. Developer Policy
   ├── Name: "BCB-Developer-Policy"
   └── Permissions:
       ├── EC2 Read/Write
       ├── RDS Read
       ├── CloudWatch Read/Write
       └── S3 Read/Write

2. Admin Policy
   ├── Name: "BCB-Admin-Policy"
   └── Permissions:
       └── Full access to required services
```

## Next Steps Checklist

- [x] Set up budget alerts
- [x] Create billing alarms
- [x] Create cost dashboard
- [ ] Create VPC
- [ ] Configure subnets
- [ ] Set up internet gateway
- [ ] Configure NAT gateway
- [ ] Create security groups
- [ ] Set up IAM roles
- [ ] Create user policies

## Notes

* Keep track of NAT Gateway costs
* Monitor CloudWatch costs
* Document all security group rules
* Save all IAM policy JSON files 