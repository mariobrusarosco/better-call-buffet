import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get connection string from .env file
DATABASE_URL = os.environ.get("DATABASE_URL")

# Remove any prefix showing in logs
print(f"Connecting to database: better_call_buffet at bcb-db.cl04u4kue30d.us-east-1.rds.amazonaws.com")

try:
    # Connect to the database
    conn = psycopg2.connect(DATABASE_URL)
    
    # Create a cursor
    cursor = conn.cursor()
    
    # Execute a test query
    cursor.execute("SELECT version();")
    
    # Fetch the result
    version = cursor.fetchone()
    print(f"Connection successful!")
    print(f"PostgreSQL version: {version[0]}")
    
    # Close the connection
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Error connecting to the database: {e}") 