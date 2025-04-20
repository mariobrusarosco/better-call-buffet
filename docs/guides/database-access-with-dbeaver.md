# Database Access Guide: Using DBeaver with Better Call Buffet

This guide explains how to connect to and work with the Better Call Buffet PostgreSQL database using DBeaver, a popular free and open-source database management tool.

## Table of Contents

1. [Introduction](#introduction)
2. [Installing DBeaver](#installing-dbeaver)
3. [Connecting to Local Development Database](#connecting-to-local-development-database)
4. [Connecting to Production Database](#connecting-to-production-database)
5. [Working with Database Objects](#working-with-database-objects)
6. [Running SQL Queries](#running-sql-queries)
7. [Exporting and Importing Data](#exporting-and-importing-data)
8. [Troubleshooting](#troubleshooting)

## Introduction

DBeaver is a universal database management tool that supports a wide range of database systems, including PostgreSQL. It offers a user-friendly interface for database administration, SQL development, and data analysis.

Key features include:
- SQL editor with syntax highlighting and autocompletion
- Data editor for viewing and modifying table data
- Visual query builder
- ER diagrams and database schema visualization
- Export/import functionality
- Support for various database objects (tables, views, procedures, etc.)

## Installing DBeaver

1. **Download DBeaver**:
   - Visit the [DBeaver website](https://dbeaver.io/download/)
   - Choose the appropriate version for your operating system (Windows, macOS, or Linux)

2. **Installation**:
   - **Windows**: Run the installer and follow the prompts
   - **macOS**: Open the DMG file and drag DBeaver to your Applications folder
   - **Linux**: Use the provided package manager commands or run the installer

3. **First Launch**:
   - Start DBeaver
   - You may be prompted to select a workspace location (the default is usually fine)
   - The application will launch with the "Database Navigator" pane visible

## Connecting to Local Development Database

When working with the Better Call Buffet application locally using Docker, follow these steps to connect to the database:

1. **Make sure Docker is running** with the application containers:
   ```bash
   docker-compose up -d
   ```

2. **In DBeaver, create a new connection**:
   - Click on "New Database Connection" in the toolbar or go to Database → New Database Connection
   - Select "PostgreSQL" from the database options and click "Next"

3. **Enter the connection details**:
   - **Host**: `localhost`
   - **Port**: `5432`
   - **Database**: `better_call_buffet`
   - **Username**: `postgres`
   - **Password**: `postgres`

4. **Test the connection**:
   - Click the "Test Connection" button
   - If successful, you'll see a "Connected" message
   - If not, check that your Docker containers are running and the PostgreSQL port is properly mapped

5. **Finish**:
   - Click "Finish" to create the connection
   - The database will appear in the Database Navigator pane

## Connecting to Production Database

To connect to the production database on AWS RDS, you'll need the appropriate credentials and possibly an SSH tunnel or VPN connection depending on your security setup.

1. **Obtain the connection information** from your DevOps team or from the AWS Console
   - RDS endpoint
   - Port (typically 5432)
   - Database name
   - Username and password

2. **In DBeaver, create a new connection**:
   - Click on "New Database Connection"
   - Select "PostgreSQL"

3. **Enter the connection details**:
   - **Host**: `[RDS-endpoint]` (e.g., `************.amazonaws.com`)
   - **Port**: `5432`
   - **Database**: `better_call_buffet`
   - **Username**: `[your-production-username]`
   - **Password**: `[your-production-password]`

4. **SSH Tunnel** (if required):
   - If the database is not publicly accessible, you may need to use an SSH tunnel
   - In the connection settings, go to the "SSH" tab
   - Enable "Use SSH tunnel"
   - Configure with your bastion host details:
     - **Host**: Your bastion/jump server address
     - **Username**: SSH username
     - **Authentication**: Password or Public Key as appropriate

5. **SSL Configuration** (if required):
   - If RDS requires SSL, go to the "SSL" tab in the connection settings
   - Enable "Use SSL"
   - Configure as needed

6. **Test and finish** the connection setup

## Working with Database Objects

Once connected, you can explore and work with database objects:

1. **Browsing Schemas and Tables**:
   - Expand your connection in the Database Navigator
   - Expand "Schemas" → "public"
   - You'll see folders for Tables, Views, etc.

2. **Viewing Table Structure**:
   - Select a table (e.g., "accounts")
   - The properties pane will show details including columns, constraints, etc.
   - You can also right-click on a table and select "View" or "Edit" to see its structure

3. **Creating New Objects**:
   - Right-click on the appropriate folder (e.g., "Tables")
   - Select "Create New [Object]"
   - Follow the wizard to create the object

4. **Modifying Objects**:
   - Right-click on the object and select "Alter [Object]" or use the properties pane
   - Make your changes and save

## Running SQL Queries

DBeaver provides a powerful SQL editor:

1. **Opening a SQL Editor**:
   - Right-click on your database connection and select "SQL Editor"
   - Or click on the "SQL" button in the toolbar

2. **Writing and Executing Queries**:
   - Type your SQL query in the editor
   - Execute by pressing F5, Ctrl+Enter, or the "Execute" button
   - Results appear in the lower pane

3. **Example Queries for Better Call Buffet**:

   **View all accounts**:
   ```sql
   SELECT * FROM accounts;
   ```

   **Check account balances**:
   ```sql
   SELECT name, balance, currency FROM accounts WHERE is_active = true;
   ```

   **Filter by account type**:
   ```sql
   SELECT * FROM accounts WHERE type = 'savings';
   ```

## Exporting and Importing Data

DBeaver offers several options for data import/export:

1. **Exporting Data**:
   - Right-click on a table and select "Export Data"
   - Choose a format (CSV, Excel, SQL INSERT statements, etc.)
   - Configure the export options and complete the wizard

2. **Importing Data**:
   - Right-click on a table and select "Import Data"
   - Choose the source format and file
   - Map columns and configure import settings
   - Complete the import

3. **Database Dump/Restore**:
   - For PostgreSQL databases, you can use the "Tools" menu
   - Select "Database → Dump Database" or "Database → Restore Database"
   - Configure the options and proceed

## Troubleshooting

### Common Connection Issues

1. **Connection Refused**:
   - Check if the database server is running
   - Verify the hostname and port
   - Check if any firewall is blocking the connection

2. **Authentication Failed**:
   - Double-check username and password
   - Ensure the user has access to the specified database

3. **Database Not Found**:
   - Verify the database name
   - Check if the database exists on the server

4. **SSH Tunnel Issues**:
   - Verify SSH credentials and host information
   - Check if the SSH server allows tunneling

### Performance Tips

1. **Limit Result Sets**:
   - Use LIMIT clauses in your queries to reduce data transfer
   - Consider pagination for large result sets

2. **Connection Pooling**:
   - In DBeaver Preferences, you can configure connection pooling settings
   - This can improve performance for frequent connections

3. **Query Optimization**:
   - Use the "Explain Plan" feature to analyze query performance
   - Right-click in a query and select "Explain Execution Plan"

## Conclusion

DBeaver provides a comprehensive set of tools for working with the Better Call Buffet database. By following this guide, you should be able to connect to both development and production databases, explore and modify database objects, run queries, and import/export data as needed.

For more advanced features and detailed documentation, visit the [official DBeaver documentation](https://dbeaver.com/docs/wiki/). 