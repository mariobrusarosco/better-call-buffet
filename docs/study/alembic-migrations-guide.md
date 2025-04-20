# Alembic Migrations Guide

## What is Alembic?

Alembic is a lightweight database migration tool for SQLAlchemy, created by Mike Bayer (the same author as SQLAlchemy). It provides a way to incrementally update your database schema over time while preserving existing data, making it possible to evolve your data model as your application grows.

## Key Features

- **Auto-generation**: Can automatically detect schema changes between your SQLAlchemy models and the database
- **Dependencies**: Migrations can depend on other migrations
- **Branching**: Supports branched migration paths
- **Flexibility**: Can execute raw SQL or use SQLAlchemy constructs
- **Environment Control**: Customizable environment contexts
- **Transactional DDL**: Runs migrations in transactions where supported

## Basic Concepts

### Revision Files

Each database change is tracked as a revision file:

```python
# versions/a1b2c3d4e5f6_create_users_table.py
"""create users table

Revision ID: a1b2c3d4e5f6
Revises: 
Create Date: 2023-07-10 14:23:45.678901

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'a1b2c3d4e5f6'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
```

### Migration Directionality

Each migration has two methods:
- `upgrade()`: Apply the migration (forward)
- `downgrade()`: Revert the migration (backward)

### Environment Configuration

Alembic uses an environment configuration to connect to your database:

```python
# alembic/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

from app.db.base import Base  # Import your SQLAlchemy models
from app.core.config import settings  # Import your app settings

# this is the Alembic Config object
config = context.config

# Set the SQLAlchemy URL from your application settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# ...rest of the file...

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=Base.metadata,
            # other options...
        )

        with context.begin_transaction():
            context.run_migrations()
```

## Setting Up Alembic

### Installation

```bash
pip install alembic

# Or with Poetry (as used in Better Call Buffet)
poetry add alembic
```

### Initialization

```bash
# Initialize Alembic in your project
alembic init alembic

# This creates:
# - alembic/ directory
# - alembic/versions/ directory (empty)
# - alembic/env.py
# - alembic/README
# - alembic/script.py.mako (template for new migrations)
# - alembic.ini
```

### Configuration

Edit `alembic.ini` to set basic options:

```ini
# alembic.ini
[alembic]
script_location = alembic
prepend_sys_path = .
# ... other settings ...
```

Edit `alembic/env.py` to configure the database connection and import your models:

```python
# alembic/env.py
# ... imports ...

# Import all SQLAlchemy models here
from app.domains.users.models import User
from app.domains.accounts.models import Account
from app.domains.categories.models import Category
from app.domains.transactions.models import Transaction

# target_metadata = Base.metadata
```

## Common Operations

### Creating Migrations

#### Auto-generating migrations

```bash
# Generate a migration automatically by comparing models to DB
alembic revision --autogenerate -m "create users table"
```

#### Writing migrations manually

```bash
# Create an empty migration file
alembic revision -m "create users table"
```

Then edit the file to add your changes manually.

### Running Migrations

```bash
# Apply all migrations
alembic upgrade head

# Apply next migration
alembic upgrade +1

# Apply specific migration
alembic upgrade a1b2c3d4e5f6

# Revert last migration
alembic downgrade -1

# Revert all migrations
alembic downgrade base
```

### Viewing Migration Status

```bash
# Show current revision
alembic current

# Show migration history
alembic history --verbose
```

## Common Migration Operations

### Tables and Columns

```python
# Create a table
op.create_table(
    'accounts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('balance', sa.Float(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
)

# Add a column
op.add_column('users', sa.Column('phone_number', sa.String(), nullable=True))

# Alter a column
op.alter_column('users', 'email', 
                existing_type=sa.VARCHAR(),
                nullable=False)

# Drop a column
op.drop_column('users', 'temporary_field')

# Drop a table
op.drop_table('discontinued_feature')
```

### Indexes and Constraints

```python
# Create an index
op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

# Create a foreign key
op.create_foreign_key(
    'fk_transactions_category_id_categories',
    'transactions', 'categories',
    ['category_id'], ['id']
)

# Create a unique constraint
op.create_unique_constraint('uq_accounts_name_user_id', 'accounts', ['name', 'user_id'])

# Drop a constraint
op.drop_constraint('uq_accounts_name_user_id', 'accounts', type_='unique')

# Drop an index
op.drop_index(op.f('ix_users_email'), table_name='users')
```

### Data Migrations

```python
# Insert data
op.bulk_insert(
    sa.table('categories',
        sa.column('id', sa.Integer()),
        sa.column('name', sa.String()),
        sa.column('type', sa.String())
    ),
    [
        {'id': 1, 'name': 'Food', 'type': 'EXPENSE'},
        {'id': 2, 'name': 'Transportation', 'type': 'EXPENSE'},
        {'id': 3, 'name': 'Salary', 'type': 'INCOME'},
    ]
)

# Update data
from sqlalchemy.sql import table, column
users = table('users',
    column('id', sa.Integer),
    column('is_active', sa.Boolean)
)

connection = op.get_bind()
connection.execute(
    users.update().
    where(users.c.id > 10).
    values(is_active=True)
)
```

## Alembic in Better Call Buffet

The Better Call Buffet project uses Alembic for database migrations. Here's how it's structured:

### Directory Structure

```
project_root/
├── alembic/
│   ├── versions/          # Migration script files
│   ├── env.py            # Configuration for migrations
│   └── script.py.mako     # Template for migration files
└── alembic.ini            # Alembic configuration file
```

### Database Configuration

The `env.py` file is configured to use the project's database URL from settings:

```python
# alembic/env.py
from app.core.config import settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
```

### Integration with Models

Migrations are auto-generated from SQLAlchemy models:

```python
# alembic/env.py
from app.db.base import Base
# Import all models
from app.domains.users.models import User
from app.domains.accounts.models import Account
from app.domains.categories.models import Category
from app.domains.transactions.models import Transaction

target_metadata = Base.metadata
```

### Migration Example

Here's an example of a migration that might be generated for the User model:

```python
"""create users table

Revision ID: a1b2c3d4e5f6
Revises: 
Create Date: 2023-07-10 15:30:45

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.current_timestamp(), 
                  onupdate=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
```

## Best Practices

1. **Always Include Downgrade Methods**: Make sure every migration can be reversed
2. **Keep Migrations Small**: Smaller, focused migrations are easier to manage
3. **Test Migrations**: Test both upgrade and downgrade paths before applying to production
4. **Don't Edit Existing Migrations**: Create new migrations instead of changing existing ones
5. **Use Transactions**: Run migrations inside transactions where possible
6. **Avoid Raw SQL**: Use SQLAlchemy constructs for better database compatibility
7. **Include Meaningful Messages**: Use clear descriptions in migration messages
8. **Version Control Migrations**: Always commit migration files to version control

## Advanced Alembic Features

### Branched Migrations

```python
# Branch identifier
branch_labels = ('feature-x',)

# Override branch merging
depends_on = 'a1b2c3d4e5f6'
```

### Running Online Migrations

Execute migrations safely on a live database:

```python
def upgrade():
    # Run an upgrade in batches to avoid locking the database
    conn = op.get_bind()
    # Migrate in smaller batches
    conn.execute(
        """
        UPDATE users 
        SET email = lower(email)
        WHERE id BETWEEN 1 AND 1000
        """
    )
    # Continue with additional batches
```

### Custom Context Functions

```python
# alembic/env.py
def process_revision_directives(context, revision, directives):
    # Custom logic for migration generation
    if context.config.cmd_opts.autogenerate:
        script = directives[0]
        # Add custom operations or modify generated migrations
```

### Multiple Databases

```python
# alembic/env.py
def run_migrations_online():
    # Configure multiple databases
    engines = {
        'main': engine_from_config(...),
        'legacy': engine_from_config(...)
    }
    
    for name, engine in engines.items():
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=Base.metadata,
                version_table=f'alembic_version_{name}'
            )
            with context.begin_transaction():
                context.run_migrations(engine_name=name)
```

## Common Issues and Solutions

### "Target Database is not up to date"

```bash
# If you get this error when auto-generating migrations
alembic revision --autogenerate -m "new migration" --head head
```

### Working with Existing Databases

For an existing database:

```bash
# Create a "blank" starting point migration
alembic revision -m "baseline"

# Then mark it as complete without running
alembic stamp head
```

### Schema Changes Not Detected

Not all changes are auto-detected:

- Adding or changing server defaults
- Changes to constraints that don't have a name
- Some column alterations
- Table and schema name changes

Always review auto-generated migrations!

## Integration with FastAPI

In FastAPI applications like Better Call Buffet, Alembic is typically integrated with the application setup:

```python
# app/db/init_db.py
from alembic.config import Config
from alembic import command

def init_db():
    # Run migrations
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    
    # Then possibly seed data
    # ...
```

## Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [Auto-generating Migrations](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)
- [Alembic Operations Reference](https://alembic.sqlalchemy.org/en/latest/ops.html)
- [SQLAlchemy + Alembic Recipe Book](https://alembic.sqlalchemy.org/en/latest/cookbook.html) 