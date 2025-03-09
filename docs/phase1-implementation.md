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

## Budget Decision: NAT Gateway Omission

**Decision**: We've decided to omit the NAT Gateway from our initial architecture due to budget constraints.

**Rationale**:
- NAT Gateway costs approximately $32/month
- Our monthly budget is capped at $25
- Initial development can proceed with all public subnets

**Implications**:
- We'll implement proper security through security groups
- We'll revisit this decision when budget allows

## VPC Setup

### 1. VPC Configuration ✅
```bash
AWS Console → VPC:

1. Create VPC
   ├── Name: "BCB-Production-VPC"
   ├── CIDR: 10.0.0.0/16
   └── Enable DNS hostnames

2. Create Subnets
   ├── Application Subnets
   │   ├── bcb-public-1a: 10.0.1.0/24 (AZ: us-east-1a)
   │   └── bcb-public-1b: 10.0.2.0/24 (AZ: us-east-1b)
   │
   └── Database Subnets (Currently Public)
       ├── bcb-public-1a-db: 10.0.11.0/24 (AZ: us-east-1a)
       └── bcb-public-1b-db: 10.0.12.0/24 (AZ: us-east-1b)
```

### 2. Internet Connectivity ✅
```bash
1. Internet Gateway
   ├── Create: "BCB-IGW"
   └── Attach to VPC

2. Public Route Table
   ├── Name: "BCB-Public-RT"
   └── Routes:
       ├── 10.0.0.0/16 → local
       └── 0.0.0.0/0 → Internet Gateway

3. Route Table Associations
   ├── Associate all subnets with Public Route Table
   └── Verify internet connectivity
```

### 3. Security Groups ✅
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
   │   └── PostgreSQL (5432) from BCB-App-SG only
   └── Outbound Rules:
       └── All traffic to anywhere
```

## IAM Configuration ✅

### 1. Service Roles ✅
```bash
1. Elastic Beanstalk Role
   ├── Name: "BCB-EB-Role"
   └── Policies:
       ├── AWSElasticBeanstalkWebTier
       ├── AWSElasticBeanstalkWorkerTier
       └── AWSElasticBeanstalkMulticontainerDocker

2. RDS Role
   ├── Name: "BCB-RDS-Role"
   └── Policies:
       └── AmazonRDSFullAccess
```

### 2. User Policies ✅
```bash
1. Developer Policy
   ├── Name: "BCB-Developer-Policy"
   └── Permissions:
       ├── EC2: Describe*, Get*, List*
       ├── Elastic Beanstalk: Describe*, List*, Check*
       ├── RDS: Describe*, List*
       ├── CloudWatch: Describe*, Get*, List*
       └── S3: Get*, List*

2. Admin Policy
   ├── Name: "BCB-Admin-Policy"
   └── Permissions:
       ├── EC2: All actions
       ├── Elastic Beanstalk: All actions
       ├── RDS: All actions
       ├── CloudWatch: All actions
       ├── S3: All actions
       └── IAM: GetRole*, ListRole*, PassRole
```

## Next Steps Checklist

- [x] Set up budget alerts
- [x] Create billing alarms
- [x] Create cost dashboard
- [x] Document NAT Gateway budget decision
- [x] Create VPC
- [x] Configure all public subnets
- [x] Set up internet gateway
- [x] Create route table
- [x] Create security groups
- [x] Set up IAM roles
- [x] Create user policies

## Phase 1 Complete! ✅

Phase 1 of the Better Call Buffet infrastructure is now complete. We have established:

1. **Cost Controls**: Budget alerts and monitoring to stay within our $25 budget
2. **Network Infrastructure**: VPC with subnets across multiple AZs
3. **Security**: Proper security groups with least privilege principle
4. **Permissions**: IAM roles and policies for service and user access
5. **Documentation**: Decision records for architectural choices

Our next phase will focus on setting up the database infrastructure.

## Notes

* Remember all subnets are public in this design
* Ensure database security group is very restrictive
* Document our "development" architecture pattern
* Plan for future migration to private subnets
* Save all IAM policy JSON files 