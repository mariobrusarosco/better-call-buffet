# SQLAlchemy Models Guide

## What is SQLAlchemy?

SQLAlchemy is a SQL toolkit and Object-Relational Mapping (ORM) library for Python that provides a set of high-level API for connecting to relational databases. Created by Mike Bayer, it gives developers the ability to interact with databases using Python objects rather than writing raw SQL.

## Key Features

- **ORM**: Maps database tables to Python classes
- **Database Agnostic**: Works with PostgreSQL, MySQL, SQLite, Oracle, and more
- **Expression Language**: Powerful SQL abstraction layer
- **Connection Pooling**: Efficient database connection management
- **Transaction Support**: ACID-compliant transaction management
- **Schema Management**: Tools for creating and modifying database schemas

## Core Concepts

### The Base Class

All SQLAlchemy models inherit from a "declarative base" class:

```python
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    # column definitions
```

### Column Definitions

Columns are defined using the `Column` class:

```python
from sqlalchemy import Column, Integer, String, Boolean

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    email = Column(String, unique=True)
    is_active = Column(Boolean, default=True)
```

### Common Column Types

| SQLAlchemy Type | Python Type | Database Type |
|-----------------|-------------|---------------|
| Integer         | int         | INTEGER       |
| String          | str         | VARCHAR       |
| Text            | str         | TEXT          |
| Boolean         | bool        | BOOLEAN       |
| Float           | float       | FLOAT/REAL    |
| DateTime        | datetime    | TIMESTAMP     |
| Date            | date        | DATE          |
| JSON            | dict        | JSON/JSONB    |
| Enum            | enum.Enum   | VARCHAR/ENUM  |

### Primary Keys and Indexes

```python
id = Column(Integer, primary_key=True, index=True)
```

- `primary_key=True`: Marks column as the primary key
- `index=True`: Creates an index on this column for faster queries

### Constraints

```python
email = Column(String, unique=True, nullable=False)
```

- `unique=True`: Column values must be unique
- `nullable=False`: Column cannot have NULL values
- `default=value`: Default value if none specified
- `server_default=text("expression")`: SQL expression for default value

## Relationships in SQLAlchemy

### Foreign Keys

Foreign keys establish a link between tables:

```python
from sqlalchemy import ForeignKey

account_id = Column(Integer, ForeignKey("accounts.id"))
```

### Relationship Types

#### One-to-Many Relationship

```python
from sqlalchemy.orm import relationship

# In the "one" side
items = relationship("Item", back_populates="owner")

# In the "many" side
owner_id = Column(Integer, ForeignKey("owners.id"))
owner = relationship("Owner", back_populates="items")
```

#### Many-to-One Relationship

This is just the reverse perspective of a one-to-many relationship.

#### One-to-One Relationship

```python
# In the parent model
profile = relationship("Profile", uselist=False, back_populates="user")

# In the child model
user_id = Column(Integer, ForeignKey("users.id"), unique=True)
user = relationship("User", back_populates="profile")
```

#### Many-to-Many Relationship

Requires an association table:

```python
# Association table (no class needed)
post_tag = Table(
    "post_tag",
    Base.metadata,
    Column("post_id", Integer, ForeignKey("posts.id")),
    Column("tag_id", Integer, ForeignKey("tags.id"))
)

# In the Post class
tags = relationship("Tag", secondary=post_tag, back_populates="posts")

# In the Tag class
posts = relationship("Post", secondary=post_tag, back_populates="tags")
```

### Self-Referential Relationships

For hierarchical data:

```python
parent_id = Column(Integer, ForeignKey("categories.id"))
children = relationship("Category", backref=backref("parent", remote_side=[id]))
```

## SQLAlchemy in Better Call Buffet

The Better Call Buffet project uses SQLAlchemy models to represent its domain entities. Let's look at specific examples:

### User Model

```python
# app/domains/users/models.py
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.db.connection_and_session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    accounts = relationship("Account", back_populates="user")
    categories = relationship("Category", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")
```

### Account Model

```python
# app/domains/accounts/models.py
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

from app.db.connection_and_session import Base

class AccountType(enum.Enum):
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT = "credit"
    CASH = "cash"
    INVESTMENT = "investment"
    OTHER = "other"

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    type = Column(String, nullable=False)
    balance = Column(Float, default=0.0)
    currency = Column(String, default="USD")
    is_active = Column(Boolean, default=True)
    
    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Category Model (Hierarchical)

```python
# app/domains/categories/models.py
class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    color = Column(String, default="#000000")
    icon = Column(String, nullable=True)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # For hierarchical categories
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    
    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="categories")
    subcategories = relationship("Category", 
                                backref="parent",
                                remote_side=[id])
    transactions = relationship("Transaction", back_populates="category")
```

### Transaction Model (Complex Relationships)

```python
# app/domains/transactions/models.py
class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    date = Column(DateTime, nullable=False)
    type = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    is_recurring = Column(Boolean, default=False)
    
    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    
    # Optional target account for transfers
    target_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="transactions")
    account = relationship("Account", back_populates="transactions", foreign_keys=[account_id])
    category = relationship("Category", back_populates="transactions")
    target_account = relationship("Account", foreign_keys=[target_account_id])
    
    # Optional parent transaction for recurring transactions
    parent_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    children = relationship("Transaction", backref="parent_transaction", remote_side=[id])
```

## Database Interaction Patterns

### Database Setup

```python
# app/db/base.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

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

### CRUD Operations

The Better Call Buffet project uses a service layer pattern for database operations:

```python
# Example from AccountService
def create(self, user_id: int, account_in: AccountCreate) -> Account:
    # Create the account
    db_account = Account(
        name=account_in.name,
        description=account_in.description,
        type=account_in.type.value,
        balance=account_in.balance,
        currency=account_in.currency,
        is_active=account_in.is_active,
        user_id=user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    self.db.add(db_account)     # Stage for commit
    self.db.commit()            # Commit to database
    self.db.refresh(db_account) # Refresh with generated values (id, etc.)
    return db_account
```

### Querying

SQLAlchemy provides a powerful query API:

```python
# Basic query
users = db.query(User).all()

# Filtering
active_users = db.query(User).filter(User.is_active == True).all()

# Pagination
users_page = db.query(User).offset(skip).limit(limit).all()

# Joining
users_with_accounts = db.query(User).join(User.accounts).all()

# Ordering
recent_users = db.query(User).order_by(User.created_at.desc()).all()

# Aggregation
from sqlalchemy import func
category_totals = db.query(
    Category.id,
    Category.name,
    func.sum(Transaction.amount).label('total_amount')
).join(Transaction).group_by(Category.id, Category.name).all()
```

## Schema Migrations

SQLAlchemy models define the database schema, but migrations are handled by Alembic:

```bash
# Generate a migration
alembic revision --autogenerate -m "Create users table"

# Apply migrations
alembic upgrade head

# Revert migrations
alembic downgrade -1
```

## Best Practices

1. **Define Clear Table Names**: Use singular form for model class names and plural for table names
2. **Use Relationship Backlinks**: Set `back_populates` or `backref` to navigate both directions
3. **Include Timestamps**: Add `created_at` and `updated_at` fields to track records
4. **Set Cascades Appropriately**: Define what happens to children when a parent is deleted
5. **Add Indexes**: Create indexes on frequently queried columns
6. **Validate Foreign Keys**: Check foreign key relationships with `db.query().first()`
7. **Use Enums for Type Fields**: Define enums for columns with a restricted set of values

## Advanced SQLAlchemy Features

### Hybrid Properties

Combine attributes with functionality:

```python
from sqlalchemy.ext.hybrid import hybrid_property

class Account(Base):
    # ... columns ...
    
    @hybrid_property
    def is_low_balance(self):
        return self.balance < 100.0
    
    @is_low_balance.expression
    def is_low_balance(cls):
        return cls.balance < 100.0
```

### Composite Keys

```python
from sqlalchemy import PrimaryKeyConstraint

class OrderItem(Base):
    __tablename__ = "order_items"
    
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)
    
    __table_args__ = (
        PrimaryKeyConstraint('order_id', 'product_id'),
    )
```

### Event Listeners

Execute code on certain events:

```python
from sqlalchemy import event

@event.listens_for(User, 'before_insert')
def hash_password(mapper, connection, target):
    target.hashed_password = hash_function(target.password)
    target.password = None
```

## Resources

- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy ORM Tutorial](https://docs.sqlalchemy.org/en/14/orm/tutorial.html)
- [SQLAlchemy ORM Examples](https://github.com/sqlalchemy/sqlalchemy/tree/main/examples/) 