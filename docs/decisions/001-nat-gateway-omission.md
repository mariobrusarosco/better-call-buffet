# Decision Record: NAT Gateway Omission (DR-001)

## Status

Accepted (March 9, 2023)

## Context

Our initial VPC design included a NAT Gateway to allow private subnet resources (like our database) to access the internet while remaining protected from inbound internet traffic. This is a standard best practice for production environments.

However, during our infrastructure cost analysis, we discovered:

- NAT Gateway costs approximately $32/month
- Our monthly infrastructure budget cap is $25
- NAT Gateway alone would exceed our entire infrastructure budget

## Decision

We have decided to omit the NAT Gateway from our initial architecture and use public subnets for all resources, including the database.

Key aspects of this decision:

- All subnets will be public with direct internet access
- Database security will rely on security groups instead of network isolation
- We will use clear naming conventions (`public-1a-db`) to indicate future migration plans
- We plan to add NAT Gateway and convert to private subnets when budget allows

## Consequences

### Positive

- Stays within our monthly budget of $25
- Simplifies initial architecture
- Reduces management overhead
- Allows progress without budget increase

### Negative

- Reduced security due to lack of network isolation
- Database instances will have public IP addresses
- Deviates from standard best practices
- Will require migration effort in the future

### Mitigations

To address the security concerns:

1. Implement strict security groups that only allow access from application tier
2. Potentially use AWS Secrets Manager for credentials
3. Enable enhanced monitoring
4. Document this as a "development" architecture pattern
5. Plan and budget for proper network isolation in the future

## Related Documents

- [VPC Design Documentation](../vpc-design.md)
- [Phase 1 Implementation](../phase1-implementation.md)

## Notes

This decision should be revisited when:

- Budget constraints change
- We move to production
- Security requirements increase
