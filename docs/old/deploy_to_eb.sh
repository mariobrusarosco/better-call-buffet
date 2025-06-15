#!/bin/bash

# Script to deploy the application to Elastic Beanstalk

set -e  # Exit on error

# Configuration
APP_NAME="better-call-buffet"
ENV_NAME="better-call-buffet-prod"
S3_BUCKET="better-call-buffet-deployments"
REGION=$(aws configure get region)
VERSION_LABEL=$(date +%Y%m%d%H%M%S)

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}====== Deploying Better Call Buffet to Elastic Beanstalk ======${NC}"
echo "Application: $APP_NAME"
echo "Environment: $ENV_NAME"
echo "Version: $VERSION_LABEL"
echo "Region: $REGION"

# Step 1: Package the application
echo -e "${YELLOW}\nStep 1: Packaging the application${NC}"
./scripts/package_for_eb.sh

ZIP_FILE=$(ls -t better-call-buffet-*.zip | head -1)

if [ ! -f "$ZIP_FILE" ]; then
    echo -e "${RED}Error: ZIP file not found${NC}"
    exit 1
fi

echo -e "${GREEN}Using package: $ZIP_FILE${NC}"

# Step 2: Create/check S3 bucket
echo -e "${YELLOW}\nStep 2: Preparing S3 bucket${NC}"
if aws s3 ls "s3://$S3_BUCKET" 2>&1 | grep -q 'NoSuchBucket'; then
    echo "Creating S3 bucket: $S3_BUCKET"
    aws s3 mb "s3://$S3_BUCKET" --region "$REGION"
else
    echo "S3 bucket exists: $S3_BUCKET"
fi

# Step 3: Upload to S3
echo -e "${YELLOW}\nStep 3: Uploading application package to S3${NC}"
aws s3 cp "$ZIP_FILE" "s3://$S3_BUCKET/" --region "$REGION"
echo -e "${GREEN}Upload completed${NC}"

# Step 4: Check if application exists
echo -e "${YELLOW}\nStep 4: Checking Elastic Beanstalk application${NC}"
if ! aws elasticbeanstalk describe-applications --application-names "$APP_NAME" --region "$REGION" 2>&1 | grep -q "$APP_NAME"; then
    echo "Application does not exist, creating: $APP_NAME"
    aws elasticbeanstalk create-application --application-name "$APP_NAME" --region "$REGION"
else
    echo "Application exists: $APP_NAME"
fi

# Step 5: Create application version
echo -e "${YELLOW}\nStep 5: Creating application version${NC}"
aws elasticbeanstalk create-application-version \
    --application-name "$APP_NAME" \
    --version-label "$VERSION_LABEL" \
    --source-bundle S3Bucket="$S3_BUCKET",S3Key="$ZIP_FILE" \
    --region "$REGION"
echo -e "${GREEN}Application version created: $VERSION_LABEL${NC}"

# Step 6: Check if environment exists
echo -e "${YELLOW}\nStep 6: Checking Elastic Beanstalk environment${NC}"
if ! aws elasticbeanstalk describe-environments --application-name "$APP_NAME" --environment-names "$ENV_NAME" --region "$REGION" 2>&1 | grep -q "$ENV_NAME"; then
    echo -e "${YELLOW}Environment does not exist: $ENV_NAME${NC}"
    echo -e "${YELLOW}Please follow the deployment guide to create a new environment${NC}"
    echo -e "${YELLOW}Then update it with this version using the following command:${NC}"
    echo -e "aws elasticbeanstalk update-environment --environment-name $ENV_NAME --version-label $VERSION_LABEL --region $REGION"
else
    # Step 7: Update environment
    echo -e "${YELLOW}\nStep 7: Updating environment with new version${NC}"
    aws elasticbeanstalk update-environment \
        --environment-name "$ENV_NAME" \
        --version-label "$VERSION_LABEL" \
        --region "$REGION"
    echo -e "${GREEN}Deployment initiated${NC}"
    
    # Step 8: Wait for deployment to complete
    echo -e "${YELLOW}\nStep 8: Waiting for deployment to complete...${NC}"
    aws elasticbeanstalk wait environment-updated \
        --environment-names "$ENV_NAME" \
        --version-labels "$VERSION_LABEL" \
        --region "$REGION"
    
    # Get health status
    HEALTH=$(aws elasticbeanstalk describe-environments \
        --environment-names "$ENV_NAME" \
        --region "$REGION" \
        --query "Environments[0].Health" \
        --output text)
    
    if [ "$HEALTH" == "Green" ]; then
        echo -e "${GREEN}Deployment completed successfully!${NC}"
    else
        echo -e "${YELLOW}Deployment completed, but environment health is: $HEALTH${NC}"
        echo -e "${YELLOW}Check the Elastic Beanstalk console for more details${NC}"
    fi
    
    # Get environment URL
    URL=$(aws elasticbeanstalk describe-environments \
        --environment-names "$ENV_NAME" \
        --region "$REGION" \
        --query "Environments[0].CNAME" \
        --output text)
    
    echo -e "${GREEN}Application available at: http://$URL${NC}"
fi

echo -e "${YELLOW}\n====== Deployment Process Complete ======${NC}" 