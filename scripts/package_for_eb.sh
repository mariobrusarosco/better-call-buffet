#!/bin/bash
# Script to package the application for Elastic Beanstalk deployment

# Exit immediately if a command fails
set -e

# Configuration
APP_NAME="better-call-buffet"
VERSION=$(date +"%Y%m%d%H%M%S")
ZIP_FILE="${APP_NAME}-${VERSION}.zip"
EB_PLATFORM="Python 3.8"

echo "Packaging application for Elastic Beanstalk deployment..."
echo "Version: ${VERSION}"

# Create .ebignore file if it doesn't exist
if [ ! -f .ebignore ]; then
  echo "Creating .ebignore file..."
  cat > .ebignore << EOF
.git/
.github/
.gitignore
.idea/
.vscode/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
venv/
.venv/
env/
ENV/
scripts/
tests/
*.sh
*.md
.DS_Store
EOF
  echo ".ebignore file created."
fi

# Create Procfile if it doesn't exist
if [ ! -f Procfile ]; then
  echo "Creating Procfile..."
  echo "web: python -m uvicorn app.main:app --host 0.0.0.0 --port \$PORT" > Procfile
  echo "Procfile created."
fi

# Create .ebextensions directory if it doesn't exist
if [ ! -d .ebextensions ]; then
  echo "Creating .ebextensions directory..."
  mkdir -p .ebextensions
  echo ".ebextensions directory created."
fi

# Create Python config
if [ ! -f .ebextensions/01_python.config ]; then
  echo "Creating Python configuration..."
  cat > .ebextensions/01_python.config << EOF
option_settings:
  aws:elasticbeanstalk:container:python:
    WSGIPath: app.main:app
  aws:elasticbeanstalk:application:environment:
    PYTHONPATH: "/var/app/current"
EOF
  echo "Python configuration created."
fi

# Create logging config
if [ ! -f .ebextensions/02_logging.config ]; then
  echo "Creating logging configuration..."
  cat > .ebextensions/02_logging.config << EOF
files:
  "/opt/elasticbeanstalk/tasks/publishlogs.d/better-call-buffet.conf":
    mode: "000755"
    owner: root
    group: root
    content: |
      /var/app/current/logs/*.log
      /var/app/current/logs/*.err
      
  "/etc/logrotate.elasticbeanstalk.hourly/logrotate.elasticbeanstalk.better-call-buffet.conf":
    mode: "000755"
    owner: root
    group: root
    content: |
      /var/app/current/logs/*.log {
        size 10M
        rotate 5
        missingok
        compress
        notifempty
        copytruncate
        dateext
        dateformat -%Y%m%d-%H%M%S
      }
EOF
  echo "Logging configuration created."
fi

# Create requirements.txt from poetry if it exists and if requirements.txt doesn't exist
if [ -f pyproject.toml ] && [ ! -f requirements.txt ]; then
  echo "Creating requirements.txt from Poetry..."
  # Using pip freeze as an alternative if poetry export is not available
  poetry run pip freeze > requirements.txt
  echo "requirements.txt created."
fi

# Create logs directory if it doesn't exist
if [ ! -d logs ]; then
  echo "Creating logs directory..."
  mkdir -p logs
  touch logs/app.log
  echo "Logs directory created."
fi

# Create zip file for deployment
echo "Creating zip file: ${ZIP_FILE}..."
zip -r "${ZIP_FILE}" . -x "*.git*" "*.idea*" "*.vscode*" "__pycache__/*" "*.pyc" "venv/*" ".venv/*" "env/*" "ENV/*" "scripts/*" "tests/*" "*.sh" "*.md" ".DS_Store"
echo "Zip file created: ${ZIP_FILE}"

echo "Package ready for deployment!"
echo "To deploy to Elastic Beanstalk:"
echo "1. Go to AWS Console > Elastic Beanstalk"
echo "2. Create a new application or environment"
echo "3. Upload ${ZIP_FILE}"
echo "4. Configure environment properties"
echo ""
echo "Or use AWS CLI:"
echo "aws elasticbeanstalk create-application-version --application-name ${APP_NAME} --version-label ${VERSION} --source-bundle S3Bucket=YOUR_BUCKET,S3Key=${ZIP_FILE}"
echo "aws elasticbeanstalk update-environment --environment-name ${APP_NAME}-prod --version-label ${VERSION}" 