# Data Validation (app/domains/users/schemas.py)

## Pydantic Models

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None

## Data Validation

# Service Layer (app/domains/users/service.py)

class UserService:
    def create(self, user_in: UserCreate) -> User