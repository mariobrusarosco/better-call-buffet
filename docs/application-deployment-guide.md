# Application Deployment Guide

This guide provides step-by-step instructions for deploying the Better Call Buffet FastAPI application to AWS Elastic Beanstalk.

## Prerequisites

Before deploying the application, ensure you have:

1. AWS account with appropriate permissions
2. AWS CLI installed and configured
3. Completed VPC and RDS setups (Phase 1 and 2)
4. Working FastAPI application code

## Deployment Process

### Option 1: Using the Packaging Script and AWS Console (Recommended)

1. **Prepare deployment package**:

   ```bash
   # From the project root
   ./scripts/package_for_eb.sh
   ```

   This script will:
   - Create necessary configuration files (.ebextensions, Procfile)
   - Generate requirements.txt from Poetry dependencies
   - Package the application into a ZIP file
   - Example output: `better-call-buffet-20250420143711.zip`

2. **Deploy to AWS Elastic Beanstalk via Console**:

   a. **Log in to AWS Console**:
      - Navigate to https://console.aws.amazon.com/
      - Sign in with your AWS credentials
      - Select the AWS region you want to deploy to

   b. **Navigate to Elastic Beanstalk**:
      - In the AWS Console search bar, type "Elastic Beanstalk"
      - Select "Elastic Beanstalk" from the search results

   c. **Create a New Application** (first time only):
      - Click "Create application"
      - Enter "better-call-buffet" for Application name
      - Add optional tags if needed
      - Click "Create"

   d. **Create a New Environment**:
      - In your application dashboard, click "Create environment"
      - Select "Web server environment"
      - Click "Select"

   e. **Configure Environment Details**:
      - **Environment information**:
        - Environment name: `better-call-buffet-prod`
        - Domain: (use the default or customize)
      - **Platform**:
        - Platform: Python
        - Platform branch: Python 3.8
        - Platform version: (choose the latest recommended)

   f. **Upload Application Code**:
      - Select "Upload your code"
      - Click "Choose file" and select the ZIP file created by the packaging script (e.g., `better-call-buffet-20250420143711.zip`)
      - Enter a meaningful version label (or use the timestamp from the filename)
      - Click "Upload"

   g. **Configure Service Access**:
      - Create and use these service roles (or select existing ones):
        - Service role: `aws-elasticbeanstalk-service-role`
        - EC2 instance profile: `aws-elasticbeanstalk-ec2-role`

   h. **Configure Networking**:
      - VPC: Select your project VPC (e.g., `BCB-Production-VPC`)
      - Public IP address: Enabled
      - Instance subnets: Select your public subnets (e.g., `bcb-public-1a`, `bcb-public-1b`)
      - Instance security groups: Select your app security group (e.g., `BCB-App-SG`)
      - Database subnets: Select your private subnets (if applicable)

   i. **Configure Instance Options**:
      - Instance types: t2.micro (or appropriate size for your needs)
      - Root volume: General Purpose SSD (gp2), 10 GB

   j. **Configure Capacity**:
      - Environment type: Load balanced
      - Min instances: 1
      - Max instances: 2
      - Scaling triggers: CPUUtilization (High: 70%, Low: 30%)

   k. **Configure Software**:
      - Click "Edit" in the Software section
      - Add Environment properties (crucial for your application to work):
        ```
        DATABASE_URL=postgresql://bcb_app:YourPassword@your-rds-endpoint.amazonaws.com:5432/better_call_buffet
        PROJECT_NAME=Better Call Buffet
        SECRET_KEY=your-secret-key-here
        API_V1_PREFIX=/api/v1
        BACKEND_CORS_ORIGINS=["https://app.bettercallbuffet.com"]
        ```
      - Set the proxy server to "nginx"
      - Set the WSGI Path to "app.main:app"
      - Enable log streaming

   l. **Configure Monitoring**:
      - Health reporting: Enhanced
      - Set the health check path to `/health`
      - System: Basic health reporting
      - Managed updates: Enable weekly maintenance window

   m. **Review and Create**:
      - Review all your settings
      - Click "Submit" to create the environment

   n. **Deployment Process**:
      - AWS will now begin creating your environment and deploying your application
      - This process typically takes 5-10 minutes
      - You can monitor the progress on the environment dashboard

3. **Access Your Deployed Application**:

   - Once deployment is complete, you'll see a green checkmark and "Health: OK" status
   - The environment URL will be displayed (e.g., `better-call-buffet-prod.us-east-1.elasticbeanstalk.com`)
   - Click the URL to access your application
   - Verify that all endpoints are working correctly:
     - API documentation: `https://your-env-url/docs`
     - Health check: `https://your-env-url/health`

4. **Troubleshooting Deployment Issues**:

   If your deployment fails or the application doesn't work:
   
   - Check the environment logs:
     - Go to your environment dashboard
     - Click "Logs" in the left menu
     - Request "Last 100 lines of logs" or "Full logs"
   
   - Common issues:
     - Environment variables missing or incorrect (especially DATABASE_URL)
     - Security groups not allowing traffic between app and database
     - Python requirements installation failures
     - Application code errors

### Option 2: Using GitHub Actions (CI/CD)

1. **Set up GitHub Secrets**:

   In your GitHub repository:
   - Go to Settings → Secrets → Actions
   - Add the following secrets:
     - `AWS_ACCESS_KEY_ID`: Your AWS access key
     - `AWS_SECRET_ACCESS_KEY`: Your AWS secret key
     - `AWS_S3_BUCKET`: (Optional) S3 bucket for deployment packages

2. **Push Code to Main Branch**:

   The `.github/workflows/deploy-to-eb.yml` workflow will:
   - Run tests
   - Create a deployment package
   - Deploy to Elastic Beanstalk
   
   ```bash
   git add .
   git commit -m "Update application code"
   git push origin main
   ```

3. **Monitor Deployment**:

   - Check GitHub Actions tab for workflow status
   - Monitor Elastic Beanstalk console for environment health

### Option 3: Using AWS CLI

1. **Prepare deployment package**:

   ```bash
   ./scripts/package_for_eb.sh
   ```

2. **Create S3 bucket** (if needed):

   ```bash
   aws s3 mb s3://better-call-buffet-deployments
   ```

3. **Upload package to S3**:

   ```bash
   aws s3 cp better-call-buffet-[VERSION].zip s3://better-call-buffet-deployments/
   ```

4. **Create application version**:

   ```bash
   aws elasticbeanstalk create-application-version \
     --application-name better-call-buffet \
     --version-label [VERSION] \
     --source-bundle S3Bucket=better-call-buffet-deployments,S3Key=better-call-buffet-[VERSION].zip
   ```

5. **Update environment**:

   ```bash
   aws elasticbeanstalk update-environment \
     --environment-name better-call-buffet-prod \
     --version-label [VERSION]
   ```

## Post-Deployment Steps

1. **Verify Application Health**:

   - Check environment health status in Elastic Beanstalk console
   - Access the application URL provided by Elastic Beanstalk
   - Test API endpoints using Swagger UI or curl commands

   ```bash
   # Example health check
   curl https://[your-eb-domain].elasticbeanstalk.com/health
   
   # Example API call
   curl https://[your-eb-domain].elasticbeanstalk.com/api/v1/users/
   ```

2. **Set up CloudWatch Alarms**:

   ```bash
   # Using AWS Console
   AWS Console → CloudWatch → Alarms → Create Alarm
   
   # Common alarms:
   - CPU Utilization > 70% for 5 minutes
   - 5xx errors > 10 per minute
   - Response time > 2 seconds
   ```

3. **Configure Custom Domain** (optional):

   ```
   # Using AWS Console
   AWS Console → Route 53 → Hosted Zones → Create Record
   
   # Set up an alias record pointing to your Elastic Beanstalk environment
   - Record name: api.bettercallbuffet.com
   - Record type: A
   - Alias: Yes
   - Route traffic to: Alias to Elastic Beanstalk environment
   - Select your environment
   ```

## Troubleshooting

### Common Issues

1. **Deployment Failures**:

   - Check Elastic Beanstalk logs for error messages
   - Verify that all required environment variables are set
   - Ensure application code is compatible with Python 3.8

   ```bash
   # View deployment logs
   aws elasticbeanstalk retrieve-environment-info --environment-name better-call-buffet-prod --info-type tail
   ```

2. **Database Connection Issues**:

   - Verify security group settings allow traffic from Elastic Beanstalk to RDS
   - Check DATABASE_URL environment variable for correctness
   - Ensure RDS instance is running and accessible

3. **Application Errors**:

   - Check application logs in CloudWatch
   - SSH into EC2 instance for direct troubleshooting:
   
   ```bash
   # Using AWS Console
   AWS Console → Elastic Beanstalk → Environment → Logs → Request Logs
   
   # Using AWS CLI
   aws elasticbeanstalk retrieve-environment-info --environment-name better-call-buffet-prod --info-type bundle
   ```

## Maintenance and Updates

### Deploying Updates

1. **Using the packaging script**:

   ```bash
   # Create new package
   ./scripts/package_for_eb.sh
   
   # Upload through Elastic Beanstalk console or AWS CLI
   aws elasticbeanstalk create-application-version --application-name better-call-buffet --version-label [NEW_VERSION] --source-bundle S3Bucket=better-call-buffet-deployments,S3Key=better-call-buffet-[NEW_VERSION].zip
   aws elasticbeanstalk update-environment --environment-name better-call-buffet-prod --version-label [NEW_VERSION]
   ```

2. **Using GitHub Actions**:

   ```bash
   # Push changes to main branch
   git push origin main
   
   # Monitor GitHub Actions workflow
   ```

### Scaling the Application

1. **Modify environment configuration**:

   ```bash
   # Using AWS Console
   AWS Console → Elastic Beanstalk → Environment → Configuration → Capacity
   
   # Adjust:
   - Min/Max instance count
   - Instance types
   - Scaling triggers
   ```

2. **Using AWS CLI**:

   ```bash
   aws elasticbeanstalk update-environment \
     --environment-name better-call-buffet-prod \
     --option-settings file://scaled-options.json
   ```

## Security Considerations

1. **Environment Variables**:
   - Never commit sensitive values to version control
   - Use AWS Systems Manager Parameter Store for sensitive values

2. **Security Groups**:
   - Restrict inbound traffic to necessary ports
   - Use security group references for RDS access

3. **HTTPS**:
   - Configure SSL/TLS certificate with ACM
   - Set up HTTPS listener on load balancer

4. **IAM Permissions**:
   - Use least privilege principle for IAM roles
   - Regularly audit and rotate credentials

## Conclusion

This deployment guide provides the necessary steps to deploy the Better Call Buffet FastAPI application to AWS Elastic Beanstalk. For additional details or advanced configurations, refer to the AWS Elastic Beanstalk documentation or contact the project maintainers. 