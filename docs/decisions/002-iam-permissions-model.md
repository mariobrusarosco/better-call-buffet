# Decision Record: IAM Permissions Model (DR-002)

## Status

Accepted (March 9, 2023)
Updated (March 9, 2023)

## Context

As we build out our AWS infrastructure, we need to establish a permissions model that balances security with operational needs. We need to determine:

1. What service roles are needed for our infrastructure components
2. What permission levels different users should have
3. How to implement the principle of least privilege while maintaining operational efficiency

## Decision

We have decided to implement a two-tier IAM permissions model with separate service roles for infrastructure components:

### Service Roles

1. **Elastic Beanstalk Role (BCB-EB-Role)**

   - **Original Plan**: Web tier, worker tier, and multicontainer Docker policies
   - **Actual Implementation**: AWS pre-selected policies:
     - AWSElasticBeanstalkEnhancedHealth
     - AWSElasticBeanstalkService
   - Purpose: Allow Elastic Beanstalk to manage EC2 instances and other resources

2. **RDS Role (BCB-RDS-Role)**
   - Permissions: AmazonRDSFullAccess
   - Purpose: Allow RDS service to manage database resources

### User Policies

1. **Developer Policy (BCB-Developer-Policy)**

   - Permissions: Read access to most services, limited write access
   - Read-only: RDS, EC2, Elastic Beanstalk
   - Read/write: CloudWatch, S3
   - Purpose: Allow developers to view resources and logs without modifying critical infrastructure

2. **Admin Policy (BCB-Admin-Policy)**
   - Permissions: Full access to infrastructure services with limitations on IAM
   - Purpose: Allow administrators to manage all aspects of the infrastructure

## Implementation Notes

### AWS Pre-selected Policies

During implementation, we discovered that AWS now provides pre-selected policies for Elastic Beanstalk roles that combine the necessary permissions. This simplifies role creation and ensures all required permissions are included:

- **AWSElasticBeanstalkEnhancedHealth**: Allows Elastic Beanstalk to monitor instance health
- **AWSElasticBeanstalkService**: Provides core permissions needed to manage Elastic Beanstalk environments

These pre-selected policies cover the permissions we originally planned to include and are maintained by AWS to ensure they stay current with service requirements.

## Alternatives Considered

### Single Role/Policy Approach

- **Pros**: Simplicity, easier management
- **Cons**: Violates principle of least privilege, security risks
- **Why Rejected**: Increased security risk of accidental or malicious changes

### Role-Based Access Control (RBAC) with Many Granular Roles

- **Pros**: Most secure, highly granular control
- **Cons**: Complex to manage, operational overhead
- **Why Rejected**: Excessive complexity for our current team size and needs

## Consequences

### Positive

- Clear separation of developer and admin responsibilities
- Principle of least privilege applied at a reasonable level
- Service roles properly scoped for their functions
- Reduced risk of accidental infrastructure changes
- AWS-maintained policies reduce maintenance burden

### Negative

- Some management overhead in maintaining multiple policies
- Potential for permission issues during development
- May need refinement as application grows
- Less visibility into exact permissions in AWS-managed policies

### Mitigations

- Document the permission model clearly
- Establish process for temporary permission elevation when needed
- Review and update permissions model quarterly
- Review AWS-managed policy changes periodically

## Implementation Plan

1. Create service roles first (Elastic Beanstalk and RDS)
   - Use AWS pre-selected policies where appropriate
2. Create admin policy for initial infrastructure setup
3. Create developer policy for day-to-day operations
4. Assign policies to appropriate users/groups

## Related Documents

- [Phase 1 Implementation](../phase1-implementation.md)
- [Infrastructure Setup](../infra-setup.md)

## Notes

- This permissions model should be reviewed when:
  - Team size changes significantly
  - New AWS services are added to our infrastructure
  - Security requirements change
  - Operational issues arise from permissions constraints
  - AWS updates their managed policies
