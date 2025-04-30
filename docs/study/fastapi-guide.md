# FastAPI Guide

## What is FastAPI?

FastAPI is a modern, high-performance web framework for building APIs with Python based on standard Python type hints. Created by Sebastián Ramírez, it's designed to be fast to code, fast to run, and easy to learn.

## Key Features

- **Fast**: One of the [fastest Python frameworks available](https://fastapi.tiangolo.com/#performance), on par with NodeJS and Go
- **Type Hinting**: Leverages Python type hints for request/response validation, auto-documentation, and editor support
- **Automatic Docs**: Generates interactive API documentation (Swagger UI and ReDoc) automatically
- **Standards-Based**: Built on OpenAPI and JSON Schema standards
- **Asynchronous**: Full support for async/await syntax
- **Dependency Injection**: Built-in dependency injection system

## Installation

FastAPI is usually installed with Uvicorn, an ASGI server:

```bash
pip install fastapi uvicorn

# Or with Poetry (as used in Better Call Buffet)
poetry add fastapi uvicorn
```

## Basic Example

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}
```

Run with:

```bash
uvicorn main:app --reload
```

## Key Concepts in FastAPI

### Path Operations

In FastAPI, "path operations" refer to the combination of:
- A **path** (like `/users` or `/items/{item_id}`)
- An HTTP **method** (like GET, POST, PUT, DELETE)
- A Python **function** that handles the request

```python
@app.get("/users/{user_id}")     # Path with path parameter
def read_user(user_id: int):     # Function with type-hinted parameter
    return {"user_id": user_id}
```

### Request Body

Define request bodies using Pydantic models:

```python
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    description: str = None
    price: float
    tax: float = None

@app.post("/items/")
def create_item(item: Item):
    return item
```

### Query Parameters

Query parameters are automatically parsed from the URL:

```python
@app.get("/items/")
def read_items(skip: int = 0, limit: int = 10):
    return {"skip": skip, "limit": limit}
```

### Path Parameters

Path parameters are part of the URL path:

```python
@app.get("/items/{item_id}")
def read_item(item_id: int):
    return {"item_id": item_id}
```

### Dependency Injection

FastAPI's dependency injection system helps with:
- Sharing code logic
- Security, database connections, etc.
- Reducing code duplication

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/users/")
def read_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users
```

## FastAPI in Better Call Buffet

In the Better Call Buffet project, FastAPI is used with a domain-driven design approach:

### Project Structure

```
app/
├── api/
│   └── v1/
│       └── api.py           # API router configuration
├── core/
│   └── config.py           # Core configuration
├── db/
│   └── base.py            # Database configuration
├── domains/               # Business domains
│   ├── users/            
│   ├── accounts/         
│   ├── categories/        
│   └── transactions/
└── main.py              # Application entry point
```

### Main Application Setup

The `main.py` file initializes the FastAPI application:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.api import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json"
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
```

### API Routing

The API is organized by domains, with each domain having its own router:

```python
# app/api/v1/api.py
from fastapi import APIRouter

from app.domains.users.router import router as users_router
from app.domains.accounts.router import router as accounts_router
from app.domains.categories.router import router as categories_router
from app.domains.transactions.router import router as transactions_router

api_router = APIRouter()

api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(accounts_router, prefix="/accounts", tags=["accounts"])
api_router.include_router(categories_router, prefix="/categories", tags=["categories"])
api_router.include_router(transactions_router, prefix="/transactions", tags=["transactions"])
```

### Domain-Specific Routers

Each domain has its own router that defines the endpoints:

```python
# app/domains/accounts/router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.connection_and_session import get_db
from app.domains.accounts.schemas import Account, AccountCreate
from app.domains.accounts.service import AccountService

router = APIRouter()

@router.post("/", response_model=Account)
def create_account(
    account_in: AccountCreate,
    user_id: int,  # This will be replaced with actual auth mechanism
    db: Session = Depends(get_db)
):
    account_service = AccountService(db)
    return account_service.create(user_id=user_id, account_in=account_in)
```

### Schemas with Pydantic

Pydantic models are used for request/response validation:

```python
# app/domains/accounts/schemas.py
from pydantic import BaseModel
from typing import Optional
from enum import Enum

class AccountType(str, Enum):
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT = "credit"
    CASH = "cash"
    INVESTMENT = "investment"
    OTHER = "other"

class AccountBase(BaseModel):
    name: str
    description: Optional[str] = None
    type: AccountType
    balance: float = 0.0
    currency: str = "USD"
    is_active: bool = True

class AccountCreate(AccountBase):
    pass

class Account(AccountBase):
    id: int
    user_id: int
    
    class Config:
        from_attributes = True
```

### Service Layer Pattern

The Better Call Buffet project uses a service layer pattern to encapsulate business logic:

```python
# app/domains/accounts/service.py
class AccountService:
    def __init__(self, db: Session):
        self.db = db
        
    def create(self, user_id: int, account_in: AccountCreate) -> Account:
        # Implementation
        pass
        
    def get_by_id(self, account_id: int) -> Optional[Account]:
        # Implementation
        pass
```

### Database Connectivity

Database operations use SQLAlchemy with FastAPI's dependency injection:

```python
# app/db/base.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

## Best Practices

1. **Organize by Domain**: Structure endpoints around business concepts rather than technical layers
2. **Use Pydantic Models**: Create separate models for requests, responses, and database operations
3. **Implement Service Layer**: Separate business logic from route handlers
4. **Dependency Injection**: Use FastAPI's dependency system for database sessions, authentication, etc.
5. **Validation**: Leverage Pydantic's validation capabilities for request/response data
6. **Documentation**: Use docstrings on path operations for better API documentation
7. **Error Handling**: Use consistent error responses with appropriate HTTP status codes

## Advanced Topics

### Background Tasks

FastAPI supports running background tasks:

```python
from fastapi import BackgroundTasks

@app.post("/send-notification/{email}")
async def send_notification(email: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(send_email_notification, email, message="Hello World")
    return {"message": "Notification sent in the background"}
```

### WebSockets

FastAPI has built-in support for WebSockets:

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message text was: {data}")
```

### Testing

FastAPI provides a TestClient for testing your API:

```python
from fastapi.testclient import TestClient

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}
```

## Resources

- [Official Documentation](https://fastapi.tiangolo.com/)
- [GitHub Repository](https://github.com/tiangolo/fastapi)
- [Tutorial: FastAPI with SQLAlchemy](https://fastapi.tiangolo.com/tutorial/sql-databases/)
- [Blog: FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices) 