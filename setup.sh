#!/bin/bash

# Set error handling
set -e

# Colors for output
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Setting up Better Call Buffet development environment...${NC}"

# Check Python version
if ! command -v python3.11 &> /dev/null; then
    echo -e "${RED}❌ Python 3.11 is not installed${NC}"
    echo -e "${YELLOW}Please install Python 3.11 from your package manager or https://www.python.org/downloads/${NC}"
    exit 1
fi

# Create and activate virtual environment
echo -e "${CYAN}🔧 Creating virtual environment...${NC}"
if [ -d ".venv" ]; then
    echo -e "${YELLOW}Found existing virtual environment, removing...${NC}"
    rm -rf .venv
fi
python3.11 -m venv .venv

# Activate virtual environment
echo -e "${CYAN}🔌 Activating virtual environment...${NC}"
source .venv/bin/activate

# Upgrade pip
echo -e "${CYAN}⬆️ Upgrading pip...${NC}"
python -m pip install --upgrade pip

# Install all dependencies
echo -e "${CYAN}📦 Installing dependencies...${NC}"
pip install fastapi==0.109.2 \
          uvicorn==0.27.1 \
          python-dotenv==1.0.1 \
          sqlalchemy==2.0.27 \
          "pydantic[email]==2.4.2" \
          pydantic-settings==2.2.1 \
          "python-jose[cryptography]==3.3.0" \
          "passlib[bcrypt]==1.7.4" \
          python-multipart==0.0.9 \
          psycopg2-binary==2.9.9 \
          alembic==1.15.2

# Install dev dependencies
echo -e "${CYAN}🔧 Installing development dependencies...${NC}"
pip install pytest==7.4.0 \
          black==23.3.0 \
          flake8==6.1.0 \
          isort==5.12.0 \
          mypy==1.5.1

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo -e "${CYAN}📝 Creating .env file from template...${NC}"
    cp .env.example .env
fi

echo -e "\n${GREEN}✅ Setup completed successfully!${NC}"
echo -e "\nTo start development:"
echo "1. Activate the virtual environment: source .venv/bin/activate"
echo "2. Start the application: uvicorn app.main:app --reload"
echo "3. Visit http://localhost:8000/docs for the API documentation"
echo -e "\nHappy coding! 🎉\n" 