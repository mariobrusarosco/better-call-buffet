# Decision Record: Elastic Beanstalk Deployment Strategy (DR-004)

## Status

Proposed (Current Date)

## Context

As part of Phase 3 of the Better Call Buffet infrastructure, we need to deploy our FastAPI application to AWS. We must determine the most appropriate deployment strategy that balances:

1. Ease of management and deployment
2. Cost efficiency for our $25/month budget
3. Scalability for future growth
4. Reliability and availability requirements
5. DevOps complexity and maintenance overhead

Our application is a FastAPI Python service that connects to an RDS PostgreSQL database (set up in Phase 2).

## Decision

We have decided to deploy the Better Call Buffet FastAPI application using AWS Elastic Beanstalk with the following configuration:

### Platform Choice
- **Python 3.8 Platform**: We'll use the native Python platform rather than Docker
- **WSGIPath**: app.main:app

### Environment Configuration
- **Environment Type**: Load balanced (minimum 1, maximum 2 instances)
- **Instance Type**: t2.micro (free tier eligible)
- **Scaling Trigger**: CPU utilization (scale up at 70%, down at 30%)
- **Deployment Policy**: All-at-once for development speed

### Support Configuration
- **.ebextensions**: Custom configurations for application setup
- **Procfile**: Runtime process definition for uvicorn
- **CloudWatch Integration**: Log streaming and metrics enabled

## Alternatives Considered

### 1. Manual EC2 Deployment

- **Pros**: More control, potentially lower cost without load balancer
- **Cons**: Higher operational complexity, manual scaling, less managed failover
- **Why Rejected**: Higher maintenance burden and operational risk

### 2. ECS/Fargate

- **Pros**: Container-based deployment, better isolation, more portable
- **Cons**: More complex setup, higher learning curve, higher cost
- **Why Rejected**: Additional complexity without substantial benefits for our use case

### 3. AWS Lambda with API Gateway

- **Pros**: Serverless, pay per use, highly scalable
- **Cons**: Cold start issues, 30-second timeout limits, different programming model
- **Why Rejected**: Not ideal for a persistent API service with database connections

### 4. Single-Instance Elastic Beanstalk

- **Pros**: Lower cost (no load balancer), simpler configuration
- **Cons**: Lower availability, no auto-scaling, potential downtime during deployments
- **Why Rejected**: Sacrifices too much reliability; chosen load-balanced approach provides better availability/scalability

## Consequences

### Positive

- **Managed Service**: AWS handles patching, monitoring, and instance health
- **Simplified Deployment**: Easy application version management and rollbacks
- **Auto Scaling**: Automatic handling of traffic variations
- **Health Monitoring**: Built-in health checks and monitoring
- **Integration**: Works with existing VPC and RDS setup

### Negative

- **Cost**: Load balancer adds ~$16.50/month (not free tier eligible)
- **Less Control**: Less granular control than manual EC2 setup
- **Platform Constraints**: Tied to Elastic Beanstalk's supported platforms and configurations
- **Cold Starts**: Initial deployment may experience higher latency

### Mitigations

- **Cost Control**: Monitor usage carefully and consider scheduled scaling for non-peak hours
- **Configuration Files**: Use .ebextensions for customization to overcome platform limitations
- **CI/CD Integration**: Create GitHub Actions workflow for automated deployments

## Implementation Plan

1. Create package deployment script
2. Set up Elastic Beanstalk application and environment
3. Configure environment properties (database connection, etc.)
4. Deploy initial application version
5. Set up monitoring and alerts
6. Create CI/CD pipeline for automated deployments

## Related Documents

- [Phase 3 Planning](../phase3-planning.md)
- [Elastic Beanstalk Explained](../elastic-beanstalk.md)
- [VPC Design Documentation](../vpc-design.md)
- [RDS Configuration Decision](003-rds-configuration-choices.md)

## Notes

This decision should be revisited if:
- Application traffic increases significantly
- Budget constraints change 
- Performance characteristics change
- Additional deployment requirements emerge 