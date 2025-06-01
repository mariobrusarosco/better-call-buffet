# Better Call Buffet

A modern web application for financial management and analysis.

## Prerequisites

- Python 3.11 or higher
- PostgreSQL (for database)

## Quick Setup

### Windows
```powershell
# Run the setup script
.\setup.ps1

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# Start the application
uvicorn app.main:app --reload
```

### Linux/macOS
```bash
# Make the setup script executable
chmod +x setup.sh

# Run the setup script
./setup.sh

# Activate the virtual environment
source .venv/bin/activate

# Start the application
uvicorn app.main:app --reload
```

## Manual Setup

If you prefer to set up manually or the setup scripts don't work for you:

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```

2. Activate the virtual environment:
   - Windows: `.\.venv\Scripts\Activate.ps1`
   - Linux/macOS: `source .venv/bin/activate`

3. Install dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

5. Start the application:
   ```bash
   uvicorn app.main:app --reload
   ```

## Development

- API documentation is available at `http://localhost:8000/docs`
- OpenAPI specification at `http://localhost:8000/openapi.json`

## Project Structure

```
better-call-buffet/
├── app/
│   ├── api/           # API endpoints
│   ├── core/          # Core functionality
│   ├── db/            # Database models and config
│   └── domains/       # Business logic domains
├── docs/              # Documentation
├── scripts/           # Utility scripts
└── tests/             # Test suite
```

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests: `pytest`
4. Format code: `black .`
5. Submit a pull request

## License

[License details here]
