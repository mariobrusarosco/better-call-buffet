# User Domain Implementation Checklist

## 1. Database Setup with Docker

- [ ] Ensure Docker and Docker Compose are installed
  - [ ] Install Docker from [docker.com](https://www.docker.com/products/docker-desktop/)
  - [ ] Verify installation with `docker --version` and `docker-compose --version`

- [ ] Start the database with Docker Compose
  ```bash
  # Start only the database service
  docker-compose up -d db
  
  # Verify the container is running
  docker ps
  
  # Check database logs if needed
  docker-compose logs db
  ```

- [ ] Access the PostgreSQL database
  ```bash
  # Connect to the database container
  docker-compose exec db psql -U postgres -d better_call_buffet
  
  # List tables (once they're created)
  \dt
  
  # Exit psql
  \q
  ```

- [ ] Create a database seed script for development
  ```bash
  # Create a seed file at db/seeds/development.sql
  mkdir -p db/seeds
  touch db/seeds/development.sql
  ```

- [ ] Add sample seed data to `db/seeds/development.sql`
  ```sql
  -- Sample users
  INSERT INTO users (email, hashed_password, full_name, is_active, created_at, updated_at)
  VALUES 
    ('admin@example.com', '$2b$12$ZobRFYdEGyHhvvVa9nRQ8..JcvjrLFnhWuJV/aR6/w/oC/YJcX/pW', 'Admin User', true, NOW(), NOW()),
    ('user@example.com', '$2b$12$ZobRFYdEGyHhvvVa9nRQ8..JcvjrLFnhWuJV/aR6/w/oC/YJcX/pW', 'Regular User', true, NOW(), NOW());
  -- Note: The hashed passwords above are for 'password123' - don't use in production!
  ```

- [ ] Update the Dockerfile to include seed data application
  - [ ] Create a script to apply seeds at `scripts/apply_seeds.sh`:
    ```bash
    #!/bin/bash
    set -e

    echo "Waiting for database to be ready..."
    # Wait for the database to be ready
    while ! pg_isready -h db -p 5432 -U postgres > /dev/null 2>&1; do
      sleep 1
    done

    echo "Running migrations..."
    # Apply migrations
    alembic upgrade head

    echo "Applying seed data..."
    # Apply seed data if ENVIRONMENT is development
    if [ "$ENVIRONMENT" = "development" ]; then
      psql -h db -U postgres -d better_call_buffet -f /app/db/seeds/development.sql
    fi

    echo "Database setup complete!"
    ```

- [ ] Make the script executable
  ```bash
  chmod +x scripts/apply_seeds.sh
  ```

- [ ] Add an entrypoint to the Dockerfile that will run migrations and seeds
  ```dockerfile
  # In Dockerfile, after COPY . .
  RUN chmod +x /app/scripts/apply_seeds.sh
  
  # Use an entrypoint script
  ENTRYPOINT ["/app/scripts/entrypoint.sh"]
  ```

- [ ] Create the entrypoint script at `scripts/entrypoint.sh`:
  ```bash
  #!/bin/bash
  set -e

  # Run database setup
  /app/scripts/apply_seeds.sh

  # Execute the main command (passed as arguments)
  exec "$@"
  ```

- [ ] Update `docker-compose.yml` to set the environment variable
  ```yaml
  web:
    # existing configuration...
    environment:
      # existing environment variables...
      - ENVIRONMENT=development
  ```

## 2. User Model Implementation

- [ ] Create the User model in `app/domains/users/models.py`
  ```python
  from datetime import datetime
  from sqlalchemy import Boolean, Column, DateTime, Integer, String
  from sqlalchemy.orm import relationship
  
  from app.db.base import Base
  
  class User(Base):
      __tablename__ = "users"
  
      id = Column(Integer, primary_key=True, index=True)
      email = Column(String, unique=True, index=True)
      hashed_password = Column(String, nullable=False)
      full_name = Column(String)
      is_active = Column(Boolean, default=True)
      created_at = Column(DateTime, default=datetime.utcnow)
      updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
  ```

- [ ] Create Alembic migration for the User model
  ```bash
  # Connect to the running container
  docker-compose exec web bash
  
  # Generate migration
  alembic revision --autogenerate -m "create users table"
  
  # Apply migration
  alembic upgrade head
  
  # Exit container
  exit
  ```

- [ ] Verify database schema
  ```bash
  # Connect to the database container
  docker-compose exec db psql -U postgres -d better_call_buffet
  
  # List tables
  \dt
  
  # Describe users table
  \d users
  
  # Exit
  \q
  ```

## 3. User Schema Implementation

- [ ] Create Pydantic schemas in `app/domains/users/schemas.py`
  ```python
  from datetime import datetime
  from typing import Optional
  from pydantic import BaseModel, EmailStr
  
  # Base User schema (shared properties)
  class UserBase(BaseModel):
      email: EmailStr
      full_name: Optional[str] = None
      is_active: bool = True
  
  # Properties to receive via API on creation
  class UserCreate(UserBase):
      password: str
  
  # Properties to receive via API on update
  class UserUpdate(UserBase):
      password: Optional[str] = None
  
  # Database User representation
  class UserInDBBase(UserBase):
      id: int
      created_at: datetime
      updated_at: datetime
  
      class Config:
          from_attributes = True
  
  # User returned from API
  class User(UserInDBBase):
      pass
  
  # User stored in DB (with hashed_password)
  class UserInDB(UserInDBBase):
      hashed_password: str
  ```

## 4. User Service Implementation

- [ ] Create user service in `app/domains/users/service.py`
  ```python
  from datetime import datetime
  from typing import List, Optional
  from sqlalchemy.orm import Session
  
  from app.core.security import get_password_hash, verify_password
  from app.domains.users.models import User
  from app.domains.users.schemas import UserCreate, UserUpdate
  
  class UserService:
      def __init__(self, db: Session):
          self.db = db
      
      def get_by_id(self, user_id: int) -> Optional[User]:
          return self.db.query(User).filter(User.id == user_id).first()
      
      def get_by_email(self, email: str) -> Optional[User]:
          return self.db.query(User).filter(User.email == email).first()
      
      def get_all(self, skip: int = 0, limit: int = 100) -> List[User]:
          return self.db.query(User).offset(skip).limit(limit).all()
      
      def create(self, user_in: UserCreate) -> User:
          db_user = User(
              email=user_in.email,
              hashed_password=get_password_hash(user_in.password),
              full_name=user_in.full_name,
              is_active=True,
              created_at=datetime.utcnow(),
              updated_at=datetime.utcnow()
          )
          self.db.add(db_user)
          self.db.commit()
          self.db.refresh(db_user)
          return db_user
      
      def update(self, user: User, user_in: UserUpdate) -> User:
          update_data = user_in.dict(exclude_unset=True)
          
          if "password" in update_data and update_data["password"]:
              update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
          
          for field, value in update_data.items():
              setattr(user, field, value)
          
          user.updated_at = datetime.utcnow()
          self.db.add(user)
          self.db.commit()
          self.db.refresh(user)
          return user
      
      def delete(self, user_id: int) -> None:
          user = self.db.query(User).filter(User.id == user_id).first()
          if user:
              self.db.delete(user)
              self.db.commit()
              
      def authenticate(self, email: str, password: str) -> Optional[User]:
          user = self.get_by_email(email=email)
          if not user or not verify_password(password, user.hashed_password):
              return None
          return user
  ```

## 5. User API Router Implementation

- [ ] Create router in `app/domains/users/router.py`
  ```python
  from typing import List
  
  from fastapi import APIRouter, Depends, HTTPException, status
  from sqlalchemy.orm import Session
  
  from app.db.base import get_db
  from app.domains.users import schemas
  from app.domains.users.service import UserService
  
  router = APIRouter()
  
  @router.post("/", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
  def create_user(
      user_in: schemas.UserCreate,
      db: Session = Depends(get_db)
  ):
      user_service = UserService(db)
      user = user_service.get_by_email(email=user_in.email)
      if user:
          raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail="Email already registered"
          )
      return user_service.create(user_in=user_in)
  
  @router.get("/", response_model=List[schemas.User])
  def read_users(
      skip: int = 0,
      limit: int = 100,
      db: Session = Depends(get_db)
  ):
      user_service = UserService(db)
      users = user_service.get_all(skip=skip, limit=limit)
      return users
  
  @router.get("/{user_id}", response_model=schemas.User)
  def read_user(
      user_id: int,
      db: Session = Depends(get_db)
  ):
      user_service = UserService(db)
      db_user = user_service.get_by_id(user_id=user_id)
      if db_user is None:
          raise HTTPException(
              status_code=status.HTTP_404_NOT_FOUND,
              detail="User not found"
          )
      return db_user
  ```

## 6. Register the User Router

- [ ] Add router to the main API router in `app/api/v1/api.py`
  ```python
  from fastapi import APIRouter

  from app.domains.users.router import router as users_router
  
  api_router = APIRouter()
  api_router.include_router(users_router, prefix="/users", tags=["users"])
  ```

## 7. Test User Endpoints

- [ ] Start the application with Docker Compose
  ```bash
  # Ensure all services are running
  docker-compose up -d
  ```

- [ ] Test user creation endpoint
  ```bash
  curl -X POST "http://localhost:8000/api/v1/users/" \
    -H "Content-Type: application/json" \
    -d '{"email": "test@example.com", "password": "password123", "full_name": "Test User"}'
  ```

- [ ] Test get users endpoint
  ```bash
  curl -X GET "http://localhost:8000/api/v1/users/"
  ```

## 8. Database Visualization with DBeaver

### DBeaver Installation

- [ ] Download and install DBeaver
  - [ ] Go to [dbeaver.io](https://dbeaver.io/download/)
  - [ ] Download the appropriate version for your OS
  - [ ] Run the installer with default options

### Connect to Project Database

- [ ] Set up a new connection
  - [ ] Click "New Database Connection" (database+ icon)
  - [ ] Select "PostgreSQL"
  - [ ] Configure the connection:
    - Host: localhost
    - Port: 5432
    - Database: better_call_buffet
    - Username: postgres
    - Password: postgres
  - [ ] Test the connection
  - [ ] Finish

### Explore the Database

- [ ] Navigate the database structure
  - [ ] Expand the "better_call_buffet" database
  - [ ] Expand "Schemas" > "public" > "Tables"
  - [ ] View the "users" table structure

- [ ] Query the users table
  - [ ] Right-click on the "users" table
  - [ ] Select "View data"
  - [ ] Run SQL queries in the SQL Editor:
    ```sql
    -- View all users
    SELECT * FROM users;
    
    -- Add a test user manually
    INSERT INTO users (email, hashed_password, full_name, is_active)
    VALUES ('admin@example.com', 'somehashvalue', 'Admin User', true);
    
    -- Update a user
    UPDATE users
    SET full_name = 'Updated Name'
    WHERE email = 'admin@example.com';
    ```

## 9. Alternative Database Viewers

### pgAdmin 4

- [ ] Download and install pgAdmin 4
  - [ ] Go to [pgadmin.org](https://www.pgadmin.org/download/)
  - [ ] Download and install
  - [ ] Connect to your PostgreSQL server with:
    - Host: localhost
    - Port: 5432
    - Database: better_call_buffet
    - Username: postgres
    - Password: postgres
  - [ ] Access the "better_call_buffet" database

### Using Visual Studio Code

- [ ] Install the "SQLTools" and "SQLTools PostgreSQL/Redshift Driver" extensions
- [ ] Configure a new connection:
  - Name: Better Call Buffet
  - Driver: PostgreSQL
  - Server: localhost
  - Port: 5432
  - Database: better_call_buffet
  - Username: postgres
  - Password: postgres
- [ ] Connect and browse the database schema

## 10. User Authentication

- [ ] Implement JWT token-based authentication
- [ ] Create login endpoint
- [ ] Add dependency for getting current user
- [ ] Test authentication flow

## Next Steps

- [ ] Add user profile functionality
- [ ] Implement password reset
- [ ] Add user roles and permissions
- [ ] Implement email verification 