# Amazon Elastic Container Registry (ECR) Guide

## Overview
Amazon ECR is a fully managed container registry service that makes it easy to store, manage, share, and deploy container images. It integrates seamlessly with Amazon ECS and provides a secure, scalable, and reliable way to store Docker images.

## Key Concepts
- **Repository**: A collection of related container images with the same name but different tags
- **Image Tag**: An identifier for different versions of the same container image
- **Registry**: The service that hosts your repositories and images
- **Authorization Token**: Used to authenticate Docker with ECR (valid for 12 hours)

## Setup Process for Better Call Buffet

### 1. Create ECR Repository
```bash
# Create repository
aws ecr create-repository \
    --repository-name better-call-buffet \
    --image-scanning-configuration scanOnPush=true \
    --region us-east-1
```

### 2. Authentication
```bash
# Get login token and authenticate Docker
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
```

### 3. Tag and Push Images
```bash
# Tag local image
docker tag better-call-buffet:latest $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/better-call-buffet:latest

# Push to ECR
docker push $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/better-call-buffet:latest
```

### 4. Pull Images
```bash
# Pull from ECR
docker pull $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/better-call-buffet:latest
```

## Best Practices
1. **Image Tagging**
   - Use semantic versioning (e.g., v1.0.0)
   - Include build/commit information
   - Never rely solely on the 'latest' tag in production

2. **Security**
   - Enable scan on push
   - Regularly review and rotate credentials
   - Use IAM roles with least privilege

3. **Lifecycle Policies**
   - Set up policies to automatically clean up unused images
   - Keep tagged releases but remove old untagged images
   - Consider cost vs. retention requirements

## Common Issues and Solutions

### Authentication Failures
- Token expired (valid for 12 hours only)
  - Solution: Re-run the login command
- IAM permissions issues
  - Solution: Verify IAM role/user has correct ECR permissions

### Push/Pull Issues
- Network connectivity
  - Solution: Check VPC endpoints and security groups
- Image size limits
  - Solution: Optimize Dockerfile and use multi-stage builds

## Integration with ECS
ECR integrates directly with ECS, allowing:
- Automatic image pulling
- Secure image access through IAM roles
- No need for external registry configuration

## Cost Considerations
- Storage pricing per GB-month
- Data transfer costs for pushing/pulling images
- Consider implementing lifecycle policies to manage costs

## Monitoring
- Use CloudWatch metrics to monitor:
  - Repository size
  - Push/pull counts
  - Authentication failures
  - API usage

## Next Steps
1. Create the ECR repository
2. Set up authentication
3. Push our first image
4. Configure ECS task definitions to use ECR images
