# Better Call Buffet Setup Script

# Ensure we stop on errors
$ErrorActionPreference = "Stop"

Write-Host "Setting up Better Call Buffet development environment..." -ForegroundColor Green

# Check if Python 3.11 is installed
$pythonPath = "C:\Program Files\Python311\python.exe"
if (-not (Test-Path $pythonPath)) {
    Write-Host "Python 3.11 not found at $pythonPath" -ForegroundColor Red
    Write-Host "Please install Python 3.11 from https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# Create and activate virtual environment
Write-Host "Creating virtual environment..." -ForegroundColor Cyan

# Try to remove existing venv if it exists
if (Test-Path ".venv") {
    Write-Host "Found existing virtual environment, removing..." -ForegroundColor Yellow
    try {
        # Kill any running Python processes from the venv
        Get-Process | Where-Object { $_.Path -like "*\.venv\Scripts\python.exe" } | Stop-Process -Force
        Start-Sleep -Seconds 1
        Remove-Item -Recurse -Force ".venv" -ErrorAction SilentlyContinue
    } catch {
        Write-Host "Warning: Could not fully remove old virtual environment. Continuing anyway..." -ForegroundColor Yellow
    }
}

# Create new virtual environment
try {
    & $pythonPath -m venv .venv
} catch {
    Write-Host "Error creating virtual environment: $_" -ForegroundColor Red
    exit 1
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
try {
    & .\.venv\Scripts\Activate.ps1
} catch {
    Write-Host "Error activating virtual environment. Trying to continue anyway..." -ForegroundColor Yellow
}

# Use full path for pip
$pipPath = ".\.venv\Scripts\pip.exe"

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Cyan
& $pipPath install --upgrade pip

# Install all dependencies
Write-Host "Installing dependencies..." -ForegroundColor Cyan
& $pipPath install fastapi==0.109.2 `
    uvicorn==0.27.1 `
    python-dotenv==1.0.1 `
    sqlalchemy==2.0.27 `
    "pydantic[email]==2.4.2" `
    pydantic-settings==2.2.1 `
    "python-jose[cryptography]==3.3.0" `
    "passlib[bcrypt]==1.7.4" `
    python-multipart==0.0.9 `
    psycopg2-binary==2.9.9 `
    alembic==1.15.2

# Install dev dependencies
Write-Host "Installing development dependencies..." -ForegroundColor Cyan
& $pipPath install pytest==7.4.0 `
    black==23.3.0 `
    flake8==6.1.0 `
    isort==5.12.0 `
    mypy==1.5.1

# Create .env file if it doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env file from template..." -ForegroundColor Cyan
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
    } else {
        Write-Host "Warning: .env.example not found. Please create .env file manually." -ForegroundColor Yellow
    }
}

Write-Host "`nSetup completed successfully!" -ForegroundColor Green
Write-Host "`nTo start development:"
Write-Host "1. Activate the virtual environment: .\.venv\Scripts\Activate.ps1"
Write-Host "2. Start the application: uvicorn app.main:app --reload"
Write-Host "3. Visit http://localhost:8000/docs for the API documentation"
Write-Host "`nHappy coding!`n"

# Pause at the end when running as administrator
if ([Security.Principal.WindowsIdentity]::GetCurrent().Groups -contains 'S-1-5-32-544') {
    Write-Host "Press any key to continue..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
} 