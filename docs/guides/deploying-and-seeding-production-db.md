# Deploying and Seeding the Production Database

This guide explains how to deploy the Better Call Buffet application to the AWS Elastic Beanstalk environment and seed the production PostgreSQL database with initial data.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Deployment Process Overview](#deployment-process-overview)
3. [Creating the Deployment Package](#creating-the-deployment-package)
4. [Deploying to Elastic Beanstalk](#deploying-to-elastic-beanstalk)
5. [Connecting to the Production Database](#connecting-to-the-production-database)
6. [Seeding the Production Database](#seeding-the-production-database)
7. [Verifying the Deployment](#verifying-the-deployment)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

Before starting the deployment process, ensure you have:

1. **AWS CLI installed and configured** with appropriate credentials
   ```bash
   aws --version
   aws configure
   ```

2. **Elastic Beanstalk CLI installed** (optional but recommended)
   ```bash
   pip install awsebcli
   eb --version
   ```

3. **Required AWS permissions** for:
   - Elastic Beanstalk
   - RDS
   - S3
   - CloudWatch

4. **Access to the production environment credentials**
   - Database connection details
   - Environment variables

## Deployment Process Overview

The deployment process consists of these main steps:

1. Package the application for deployment
2. Upload and deploy to Elastic Beanstalk
3. Connect to the production database
4. Seed the database with initial data
5. Verify the deployment

## Creating the Deployment Package

The project includes a script to create the deployment package:

```bash
# Navigate to project root
cd /path/to/better-call-buffet

# Create the deployment package
./scripts/package_for_eb.sh
```

This creates a ZIP file named `better-call-buffet-YYYYMMDDHHMMSS.zip` in the project root directory.

## Deploying to Elastic Beanstalk

You can deploy using either the AWS Management Console or the provided deployment script.

### Option 1: Using the Deployment Script

```bash
# Deploy using the script
./scripts/deploy_to_eb.sh
```

### Option 2: Deploying via AWS Management Console

1. **Log in to the AWS Console**
   - Navigate to Elastic Beanstalk service
   - Select the "better-call-buffet" application

2. **Upload the deployment package**
   - Click "Upload and Deploy"
   - Select the ZIP file created in the previous step
   - Provide a version label (e.g., "v1.2.0" or use the timestamp)
   - Click "Deploy"

3. **Monitor the deployment**
   - The console will show the deployment progress
   - Wait for the environment health to return to "OK" status

## Connecting to the Production Database

The production database is hosted on AWS RDS. To connect to it, you'll need:

1. **The database endpoint** from the RDS console or environment configuration
2. **Database credentials** (username and password)

You can connect using various methods:

### Using psql CLI from a Bastion Host

If direct access to the database is restricted, you may need to connect through a bastion host:

```bash
# Connect using psql
psql -h <rds-endpoint> -U postgres -d better_call_buffet
# Enter password when prompted
```

### Using DBeaver

See [Database Access with DBeaver Guide](./database-access-with-dbeaver.md) for detailed instructions on connecting to the production database.

## Seeding the Production Database

### Option 1: Using the Seed Script on the Elastic Beanstalk Instance

You can run the seed script directly on the Elastic Beanstalk instance:

1. **Connect to the EC2 instance**:
   ```bash
   # Get the instance ID
   aws elasticbeanstalk describe-environment-resources --environment-name better-call-buffet-prod

   # Connect via SSM or SSH
   aws ssm start-session --target <instance-id>
   # or
   ssh ec2-user@<instance-public-ip>
   ```

2. **Navigate to the application directory**:
   ```bash
   cd /var/app/current
   ```

3. **Run the seed script**:
   ```bash
   # Make sure to use the production environment variables
   sudo python scripts/seed_db.py
   ```

### Option 2: Executing SQL Script via psql

If you prefer to use SQL directly:

1. **Create SQL seed file**:
   Create a file called `seed_prod_db.sql` with the following contents:

   ```sql
   -- Seed accounts
   INSERT INTO accounts (name, description, type, balance, currency, is_active, user_id, created_at, updated_at)
   VALUES 
     ('Production Checking', 'Primary checking account', 'checking', 5000.00, 'USD', true, 1, NOW(), NOW()),
     ('Production Savings', 'Emergency fund', 'savings', 10000.00, 'USD', true, 1, NOW(), NOW()),
     ('Production Credit Card', 'Primary credit card', 'credit', 500.00, 'USD', true, 1, NOW(), NOW()),
     ('Production Investment', 'Retirement investments', 'investment', 25000.00, 'USD', true, 1, NOW(), NOW());
   ```

2. **Execute the SQL script**:
   ```bash
   psql -h <rds-endpoint> -U postgres -d better_call_buffet -f seed_prod_db.sql
   # Enter password when prompted
   ```

### Option 3: Using Python Script with Production Connection

You can modify the seed script to connect to the production database:

1. **Create a production seed script**:
   
   Create a file called `scripts/seed_prod_db.py`:

   ```python
   import os
   import sys
   from sqlalchemy import create_engine
   from sqlalchemy.orm import sessionmaker

   # Add the parent directory to the path to import app modules
   sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

   # Import models
   from app.db.base import Base
   from app.domains.accounts.models import Account, AccountType

   def seed_prod_db():
       # Production database connection string
       DATABASE_URL = "postgresql://postgres:<password>@<rds-endpoint>:5432/better_call_buffet"
       
       print(f"Connecting to production database...")
       engine = create_engine(DATABASE_URL)
       
       # Create a session
       SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
       db = SessionLocal()
       
       try:
           # Seed accounts
           print("Seeding accounts...")
           accounts = [
               Account(
                   name="Production Checking", 
                   description="Primary checking account", 
                   type=AccountType.CHECKING.value, 
                   balance=5000.00, 
                   user_id=1
               ),
               Account(
                   name="Production Savings", 
                   description="Emergency fund", 
                   type=AccountType.SAVINGS.value, 
                   balance=10000.00, 
                   user_id=1
               ),
               Account(
                   name="Production Credit Card", 
                   description="Primary credit card", 
                   type=AccountType.CREDIT.value, 
                   balance=500.00, 
                   user_id=1
               ),
               Account(
                   name="Production Investment", 
                   description="Retirement investments", 
                   type=AccountType.INVESTMENT.value, 
                   balance=25000.00, 
                   user_id=1
               )
           ]
           db.add_all(accounts)
           db.commit()
           
           print("Production database seeding complete!")
           
       except Exception as e:
           print(f"Error seeding production database: {e}")
           db.rollback()
           raise
       finally:
           db.close()

   if __name__ == "__main__":
       seed_prod_db()
   ```

2. **Run the production seed script**:
   ```bash
   python scripts/seed_prod_db.py
   ```

## Verifying the Deployment

After deployment and seeding, verify that everything is working:

1. **Check the application health**:
   ```bash
   aws elasticbeanstalk describe-environments --environment-names better-call-buffet-prod
   ```

2. **Access the application URL**:
   - Open the Elastic Beanstalk URL in a browser
   - Or use your custom domain if configured

3. **Test API endpoints**:
   ```bash
   # Check health endpoint
   curl https://<your-eb-url>/health
   
   # Check accounts endpoint (may require authentication)
   curl https://<your-eb-url>/api/v1/accounts
   ```

4. **Verify database seeding**:
   - Connect to the database using DBeaver or psql
   - Run `SELECT * FROM accounts;` to check if the accounts were created

## Troubleshooting

### Common Deployment Issues

1. **Deployment Failure**:
   - Check Elastic Beanstalk logs in the AWS Console
   - Download the full logs for detailed error messages
   - Common issues include missing environment variables or dependencies

2. **Database Connection Failures**:
   - Verify the RDS security group allows connections from the Elastic Beanstalk security group
   - Check that the DATABASE_URL environment variable is correctly set
   - Ensure the database exists and the credentials are correct

3. **Application Errors**:
   - Check CloudWatch logs for application-specific errors
   - Consider enabling enhanced monitoring for more detailed logs

### Rollback Procedure

If you need to roll back to a previous version:

1. **In the AWS Console**:
   - Go to Elastic Beanstalk → Applications → Your Application
   - Select "Application versions"
   - Find the previous working version
   - Click "Deploy" to roll back

2. **Using the CLI**:
   ```bash
   aws elasticbeanstalk update-environment \
     --environment-name better-call-buffet-prod \
     --version-label <previous-version-label>
   ```

## Conclusion

Following this guide, you should be able to deploy the Better Call Buffet application to AWS Elastic Beanstalk and seed the production database with initial data. This process ensures a smooth transition from development to production, with all the necessary data in place for the application to function correctly.

Remember to always follow security best practices when handling production credentials and data, and consider implementing CI/CD pipelines for more automated deployments in the future. 