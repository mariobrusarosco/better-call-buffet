# Database Connection Guide for Developers

This guide helps new developers on the Better Call Buffet project connect to the PostgreSQL database and perform common operations.

## Connection Information

Our PostgreSQL database is hosted on AWS RDS with the following details:

- **Host**: ************.amazonaws.com
- **Port**: 5432
- **Database Name**: better_call_buffet
- **Username**: postgres
- **Password**: _Stored in .env file_

## Connection Methods

### 1. Using `psql` Command Line

The `psql` command-line tool is the official PostgreSQL client. Here's how to use it:

```bash
# Basic connection syntax
psql -h HOSTNAME -U USERNAME -d DATABASE_NAME

# For our project
psql -h ************.amazonaws.com -U postgres -d better_call_buffet

# You'll be prompted for the password
```

### 2. Using SQLAlchemy (Our Project's ORM)

Our FastAPI application uses SQLAlchemy for database operations:

```python
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get connection string from .env file
DATABASE_URL = os.environ.get("DATABASE_URL")

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Execute a query
with engine.connect() as connection:
    result = connection.execute(text("SELECT version();"))
    for row in result:
        print(f"PostgreSQL version: {row[0]}")
```

### 4. Using DBeaver (Recommended GUI Tool)

DBeaver is a free, open-source universal database tool that works with PostgreSQL and many other database systems.

#### Installation

1. **Download DBeaver**:
   - Visit [dbeaver.io](https://dbeaver.io/download/)
   - Download the appropriate version for your operating system (Windows, macOS, or Linux)
   - Install following the prompts for your platform

#### Connecting to the BCB Database

1. **Launch DBeaver** and click "New Database Connection" (database+ icon)

2. **Select PostgreSQL** from the database list and click "Next"

3. **Enter Connection Details**:
   ```
   Main Tab:
   ├── Server Host: ************.amazonaws.com
   ├── Port: 5432
   ├── Database: better_call_buffet
   ├── Username: postgres
   └── Password: [From your .env file]
   
   SSH Tab (if using SSH tunnel):
   ├── Check "Use SSH Tunnel" if connecting through bastion host
   ├── Host/IP: [Your EC2 bastion host if applicable]
   ├── Username: [SSH username]
   └── Authentication method: Password or Key file
   
   PostgreSQL Tab:
   └── Show all databases: Check this to see all databases
   ```

4. **Test Connection** to verify the settings are correct

5. **Save the connection** with a name like "BCB-PostgreSQL"

#### Using DBeaver with Our Database

1. **Browse Database Objects**:
   - Expand your connection in the Database Navigator
   - Browse through Schemas → public → Tables
   - Right-click on tables to see available actions

2. **Execute SQL Queries**:
   - Right-click your connection and select "SQL Editor" or press F3
   - Write and execute SQL statements with Ctrl+Enter or the Run button
   - View results in the Results tab below

3. **View and Edit Data**:
   - Double-click on a table to open the data editor
   - View, filter, and edit data directly
   - Use the SQL filter icon to apply WHERE conditions

4. **Table Structure Viewing**:
   - Right-click a table → "View Table" or "View Advanced"
   - See the Properties tab for detailed column information
   - View constraints, indexes, and DDL

5. **Schema Comparison/Migration**:
   - Use Tools → Compare Schemas to track changes

6. **Creating ERD Diagrams**:
   - Right-click Database → "Create ER Diagram"
   - Drag tables from the database navigator to the diagram

7. **Importing/Exporting Data**:
   - Right-click on tables → "Export Data" or "Import Data"
   - Support for various formats including CSV, Excel, etc.

#### DBeaver Tips for BCB Developers

1. **Save Your Queries**:
   - Create a "Scripts" folder in your project to save common queries
   - Use SQL files with descriptive names for different operations

2. **Configure Auto-Commit**:
   - By default, DBeaver executes in auto-commit mode
   - Disable this for transaction operations by clicking the "Auto-Commit" toggle

3. **Create Connection Templates**:
   - Set up environments (dev, staging, production) as separate connections
   - Use connection groups to organize them

4. **Visual Query Builder**:
   - Use for complex joins by clicking "Visual Query Builder"
   - Helps with JOIN relationships visualization

5. **Data Filtering**:
   - Use Ctrl+F to open the filter panel when viewing table data
   - Set up complex filter conditions with multiple criteria

## Common Database Operations

Once connected, here are useful commands for exploring and working with the database.

### Basic Navigation

```sql
-- List all databases
\l

-- Connect to a database
\c better_call_buffet

-- List all tables
\dt

-- Describe a table
\d users

-- List schemas
\dn

-- Show database users
\du
```

### Querying Data

```sql
-- Select all users
SELECT * FROM users;

-- Select specific columns
SELECT id, email, full_name FROM users;

-- Filter with WHERE
SELECT * FROM users WHERE is_active = TRUE;

-- Order results
SELECT * FROM users ORDER BY created_at DESC;

-- Limit results
SELECT * FROM users LIMIT 10;
```

### Modifying Data

```sql
-- Insert a new user
INSERT INTO users (email, full_name, hashed_password, is_active)
VALUES ('test@example.com', 'Test User', 'hashedpassword', TRUE);

-- Update a user
UPDATE users SET full_name = 'Updated Name' WHERE id = 1;

-- Delete a user
DELETE FROM users WHERE id = 1;
```

### Working with Transactions

```sql
-- Start a transaction
BEGIN;

-- Make changes
INSERT INTO users (email, full_name) VALUES ('test@example.com', 'Test User');
UPDATE users SET is_active = FALSE WHERE email = 'old@example.com';

-- Commit changes
COMMIT;

-- Or roll back changes
ROLLBACK;
```

## Viewing Table Structure

To see the full structure of our database tables:

```sql
-- View table structure
\d+ users

-- View column details
SELECT column_name, data_type, character_maximum_length
FROM INFORMATION_SCHEMA.COLUMNS
WHERE table_name = 'users';

-- View constraints
SELECT * FROM information_schema.table_constraints
WHERE table_name = 'users';
```

## Database Schema

Our primary tables include:

- **users**: User accounts and profile information
- _(Additional tables will be added as the project expands)_

### Users Table

```
+----------------+--------------+---------------------------------------+
| Column         | Type         | Description                           |
+----------------+--------------+---------------------------------------+
| id             | INTEGER      | Primary key                           |
| email          | VARCHAR      | User's email (unique)                 |
| hashed_password| VARCHAR      | Securely stored password hash         |
| full_name      | VARCHAR      | User's full name                      |
| is_active      | BOOLEAN      | Account status flag                   |
| created_at     | TIMESTAMP    | Account creation timestamp            |
| updated_at     | TIMESTAMP    | Last update timestamp                 |
+----------------+--------------+---------------------------------------+
```

## Troubleshooting

### Common Connection Issues

1. **Connection timeout**

   - Check if your IP is allowed in the security group
   - Verify VPC settings allow connections from your location
   - Ensure the RDS instance is running

2. **Authentication failed**

   - Verify your username and password
   - Check if the database user has proper permissions

3. **Database not found**
   - Verify the database name is correct
   - Check if the database exists on the server

### Command to Check RDS Status

```bash
# Using AWS CLI
aws rds describe-db-instances --db-instance-identifier bcb-db --query 'DBInstances[0].DBInstanceStatus'
```

### Connection String Format

If you need to construct the connection string manually:

```
postgresql://username:password@hostname:port/database
```

For our project:

```
postgresql://postgres:YOUR_PASSWORD@************.amazonaws.com:5432/better_call_buffet
```

## Security Best Practices

1. **Never commit passwords** or connection strings to version control
2. **Don't share your .env file** containing credentials
3. **Use IAM authentication** for production environments when possible
4. **Limit database permissions** to what's necessary for your role
5. **Be cautious with DELETE operations** - use WHERE clauses and transactions

## Getting Help

If you encounter issues connecting to the database:

1. Check the [AWS RDS Dashboard](https://console.aws.amazon.com/rds/) for instance status
2. Review CloudWatch metrics for performance issues
3. Consult this project's database documentation
4. Reach out to the project maintainers for assistance
