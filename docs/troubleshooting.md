# Troubleshooting Guide: Better Call Buffet on Elastic Beanstalk

This guide provides solutions for common issues that might arise with the Better Call Buffet application running on AWS Elastic Beanstalk.

## Deployment Issues

### Application Fails to Deploy

**Symptoms**:
- Application creation succeeds but environment creation fails
- Environment health shows degraded or severe status
- Error in logs about missing dependencies

**Possible Causes and Solutions**:

1. **Missing Dependencies**
   ```bash
   # Check environment logs
   aws elasticbeanstalk retrieve-environment-info --environment-name better-call-buffet-prod --info-type tail
   
   # Missing dependency example fix - add to requirements.txt
   pip freeze > requirements.txt
   # Then redeploy
   ```

2. **Environment Variables Missing**
   ```bash
   # Check if environment variables are set in Elastic Beanstalk console
   # Go to Configuration → Software → Environment properties
   # Or add via CLI:
   aws elasticbeanstalk update-environment \
     --environment-name better-call-buffet-prod \
     --option-settings Namespace=aws:elasticbeanstalk:application:environment,OptionName=DATABASE_URL,Value=postgresql://user:password@hostname:5432/better_call_buffet
   ```

3. **Permission Issues with .ebextensions**
   ```bash
   # Ensure permissions are set correctly in the package
   # Use debug mode when creating the package
   ./scripts/package_for_eb.sh --debug
   
   # Files in .ebextensions should have proper formatting and permissions
   ```

## Database Connection Issues

### Application Can't Connect to RDS

**Symptoms**:
- Application logs show database connection errors
- Health check endpoint returns database unhealthy

**Possible Causes and Solutions**:

1. **Security Group Issues**
   ```bash
   # Verify DB security group allows access from App security group
   aws ec2 describe-security-groups --group-ids sg-092f4eba9d78f8bfb
   
   # Add rule if missing
   aws ec2 authorize-security-group-ingress \
     --group-id sg-092f4eba9d78f8bfb \
     --protocol tcp \
     --port 5432 \
     --source-group sg-0a216606cd71ef3b6
   ```

2. **Incorrect Connection String**
   ```bash
   # Update the environment variable
   aws elasticbeanstalk update-environment \
     --environment-name better-call-buffet-prod \
     --option-settings Namespace=aws:elasticbeanstalk:application:environment,OptionName=DATABASE_URL,Value=postgresql://postgres:password@bcb-db.cl04u4kue30d.us-east-1.rds.amazonaws.com:5432/better_call_buffet
   ```

3. **RDS Instance Not Running**
   ```bash
   # Check RDS status
   aws rds describe-db-instances --db-instance-identifier bcb-db --query "DBInstances[0].DBInstanceStatus"
   
   # Start if stopped
   aws rds start-db-instance --db-instance-identifier bcb-db
   ```

## API Endpoint Issues

### Endpoints Return 500 Errors

**Symptoms**:
- API calls returning 500 status codes
- Error logs showing exceptions

**Possible Causes and Solutions**:

1. **Code Errors**
   ```bash
   # Check application logs
   aws elasticbeanstalk retrieve-environment-info --environment-name better-call-buffet-prod --info-type tail
   
   # Common fixes:
   # - Fix code issues locally
   # - Test thoroughly before deployment
   # - Deploy fixed version
   ```

2. **Environment Configuration Mismatch**
   ```bash
   # Ensure all required environment variables are set
   # Check .env.example for required variables
   ```

3. **Database Schema Issues**
   ```bash
   # Check if database tables are created
   # Connect to database and verify tables
   psql -h bcb-db.cl04u4kue30d.us-east-1.rds.amazonaws.com -U postgres -d better_call_buffet -c "\dt"
   
   # Run schema creation script if needed
   python scripts/create_tables.py
   ```

## Scaling Issues

### Application Performance Degrades Under Load

**Symptoms**:
- Slow response times
- CPU utilization alarms triggered

**Possible Causes and Solutions**:

1. **Instance Type Too Small**
   ```bash
   # Update environment configuration
   aws elasticbeanstalk update-environment \
     --environment-name better-call-buffet-prod \
     --option-settings Namespace=aws:autoscaling:launchconfiguration,OptionName=InstanceType,Value=t3.small
   ```

2. **Not Enough Instances**
   ```bash
   # Update scaling configuration
   aws elasticbeanstalk update-environment \
     --environment-name better-call-buffet-prod \
     --option-settings Namespace=aws:autoscaling:asg,OptionName=MaxSize,Value=4
   ```

3. **Database Bottleneck**
   ```bash
   # Check RDS metrics in CloudWatch
   # Consider updating parameter group or instance type
   aws rds modify-db-instance \
     --db-instance-identifier bcb-db \
     --db-instance-class db.t3.small \
     --apply-immediately
   ```

## SSL/HTTPS Issues

### Certificate Doesn't Work

**Symptoms**:
- HTTPS connections fail
- Browser warnings about invalid certificates

**Possible Causes and Solutions**:

1. **Certificate Not Properly Attached**
   ```bash
   # Verify ACM certificate
   aws acm list-certificates
   
   # Attach certificate to load balancer
   aws elasticbeanstalk update-environment \
     --environment-name better-call-buffet-prod \
     --option-settings Namespace=aws:elb:loadbalancer,OptionName=SSLCertificateId,Value=arn:aws:acm:us-east-1:123456789012:certificate/your-cert-id
   ```

2. **Domain Mismatch**
   ```bash
   # Ensure certificate domain matches app domain
   # Create new certificate if needed
   aws acm request-certificate --domain-name api.bettercallbuffet.com
   ```

## CloudWatch Monitoring Issues

### Alarms Not Triggering or Dashboard Not Showing Data

**Symptoms**:
- Missing CloudWatch metrics
- No alarms despite issues
- Dashboard shows no data

**Possible Causes and Solutions**:

1. **Resource Names Don't Match**
   ```bash
   # Verify environment name
   aws elasticbeanstalk describe-environments --query "Environments[*].{Name:EnvironmentName,ID:EnvironmentId}"
   
   # Update dashboard with correct resource names
   ./scripts/create_cloudwatch_dashboard.sh
   ```

2. **Insufficient Permissions**
   ```bash
   # Check IAM role permissions
   aws iam get-role --role-name aws-elasticbeanstalk-service-role
   
   # Ensure it has CloudWatch permissions
   ```

## Deployment Pipeline Issues

### GitHub Actions Workflow Fails

**Symptoms**:
- CI/CD pipeline fails
- Deployment doesn't reach AWS

**Possible Causes and Solutions**:

1. **Missing Secrets**
   ```bash
   # Verify GitHub secrets are set
   # Go to GitHub repository → Settings → Secrets → Actions
   # Ensure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are set
   ```

2. **Permission Issues**
   ```bash
   # Verify IAM user has sufficient permissions
   # IAM user should have:
   # - ElasticBeanstalkFullAccess
   # - S3FullAccess (or appropriate subset)
   ```

3. **S3 Bucket Issues**
   ```bash
   # Check if S3 bucket exists
   aws s3 ls s3://better-call-buffet-deployments
   
   # Create bucket if needed
   aws s3 mb s3://better-call-buffet-deployments --region us-east-1
   ```

## General Troubleshooting Steps

1. **Check Environment Health**
   ```bash
   aws elasticbeanstalk describe-environments \
     --environment-names better-call-buffet-prod \
     --query "Environments[0].{Health:Health,Status:Status}"
   ```

2. **View Recent Events**
   ```bash
   aws elasticbeanstalk describe-events \
     --environment-name better-call-buffet-prod \
     --max-items 10
   ```

3. **Access Environment Logs**
   ```bash
   # Request logs
   aws elasticbeanstalk request-environment-info \
     --environment-name better-call-buffet-prod \
     --info-type tail
   
   # Wait a moment, then retrieve
   aws elasticbeanstalk retrieve-environment-info \
     --environment-name better-call-buffet-prod \
     --info-type tail
   ```

4. **SSH into Instance for Direct Debugging**
   ```bash
   # Get public DNS of instance
   aws ec2 describe-instances \
     --filters "Name=tag:elasticbeanstalk:environment-name,Values=better-call-buffet-prod" \
     --query "Reservations[0].Instances[0].PublicDnsName"
   
   # SSH into instance (if key pair was configured)
   ssh -i ~/.ssh/your-key.pem ec2-user@ec2-xxx-xxx-xxx-xxx.compute-1.amazonaws.com
   ```

5. **Rebuild Environment as Last Resort**
   ```bash
   # Create new environment with same parameters
   # Then swap URLs
   aws elasticbeanstalk swap-environment-cnames \
     --source-environment-name better-call-buffet-prod \
     --destination-environment-name better-call-buffet-prod-2
   ```

## Contact Support

If issues persist after trying these troubleshooting steps, contact:

- Project Maintainer: Mario Brusarosco (mario.brusarosco@gmail.com)
- AWS Support (if you have a support plan) 