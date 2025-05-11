#!/bin/bash

# Script to create security group for the Elastic Beanstalk application
# This allows web traffic to the application and app traffic to the database

set -e  # Exit on error

# Configuration
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=tag:Name,Values=BCB-Production-VPC" --query "Vpcs[0].VpcId" --output text)
APP_SG_NAME="BCB-App-SG"
DB_SG_NAME="BCB-DB-SG"

echo "====== Creating Application Security Group ======"
echo "VPC ID: $VPC_ID"

# Check if security group already exists
APP_SG_ID=$(aws ec2 describe-security-groups --filters "Name=vpc-id,Values=$VPC_ID" "Name=group-name,Values=$APP_SG_NAME" --query "SecurityGroups[0].GroupId" --output text)

if [ "$APP_SG_ID" != "None" ] && [ "$APP_SG_ID" != "" ]; then
    echo "Security group $APP_SG_NAME already exists with ID: $APP_SG_ID"
else
    # Create security group
    echo "Creating security group $APP_SG_NAME"
    APP_SG_ID=$(aws ec2 create-security-group \
        --group-name "$APP_SG_NAME" \
        --description "Security group for Better Call Buffet application" \
        --vpc-id "$VPC_ID" \
        --tag-specifications "ResourceType=security-group,Tags=[{Key=Name,Value=$APP_SG_NAME},{Key=Project,Value=BetterCallBuffet}]" \
        --query "GroupId" --output text)
    
    echo "Created security group: $APP_SG_ID"
    
    # Add inbound rules for web traffic
    echo "Adding inbound rules for web traffic"
    aws ec2 authorize-security-group-ingress \
        --group-id "$APP_SG_ID" \
        --protocol tcp \
        --port 80 \
        --cidr "0.0.0.0/0" \
        --description "Allow HTTP from anywhere"
    
    aws ec2 authorize-security-group-ingress \
        --group-id "$APP_SG_ID" \
        --protocol tcp \
        --port 443 \
        --cidr "0.0.0.0/0" \
        --description "Allow HTTPS from anywhere"
    
    # Add SSH access for debugging (optional, can be removed for production)
    aws ec2 authorize-security-group-ingress \
        --group-id "$APP_SG_ID" \
        --protocol tcp \
        --port 22 \
        --cidr "0.0.0.0/0" \
        --description "Allow SSH from anywhere (for debugging)"
    
    echo "Security group rules added"
fi

# Get DB Security Group
DB_SG_ID=$(aws ec2 describe-security-groups --filters "Name=vpc-id,Values=$VPC_ID" "Name=group-name,Values=$DB_SG_NAME" --query "SecurityGroups[0].GroupId" --output text)

if [ "$DB_SG_ID" != "None" ] && [ "$DB_SG_ID" != "" ]; then
    echo "Found Database Security Group: $DB_SG_ID"
    
    # Add rule to DB security group to allow access from App security group
    echo "Adding rule to DB security group to allow access from App security group"
    aws ec2 authorize-security-group-ingress \
        --group-id "$DB_SG_ID" \
        --protocol tcp \
        --port 5432 \
        --source-group "$APP_SG_ID" \
        --description "Allow PostgreSQL access from application" || true
    
    echo "DB security group updated"
else
    echo "Warning: Database security group $DB_SG_NAME not found"
    echo "Please create the database security group first or check the name"
fi

echo "====== Security Group Configuration Complete ======"
echo "Application Security Group ID: $APP_SG_ID"
echo "Database Security Group ID: $DB_SG_ID"
echo
echo "Next Steps:"
echo "1. Use the App Security Group ID when creating your Elastic Beanstalk environment"
echo "2. Make sure your RDS instance is using the DB Security Group" 