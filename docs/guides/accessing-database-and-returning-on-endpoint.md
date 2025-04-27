# Guide: Accessing the Database and Returning Data via Endpoints in FastAPI

This guide explains the standard pattern used in this project for accessing the database within a FastAPI endpoint and returning data to the user. It relies heavily on SQLAlchemy sessions and FastAPI's dependency injection system.

## Core Concepts

1.  **SQLAlchemy Session (`Session`)**:
    *   **What it is:** The primary interface for interacting with the database for a specific period (usually one web request). It acts as a temporary workspace or conversation.
    *   **What it does:** Manages connections, tracks object changes (Identity Map), translates Python operations to SQL, and handles transactions.
    *   **Lifecycle:** Sessions are short-lived, typically **one per web request**. Create at the start, use, commit or rollback, and close at the end.

2.  **Dependency Factory (`get_db` function)**:
    *   **Purpose:** Instead of creating sessions directly in route handlers, we use a factory function (like `get_db`) to manage the session's lifecycle (creation and cleanup).
    *   **Mechanism:** It's usually a Python generator function using `yield`.
        ```python
        # Example (e.g., in app/db/base.py)
        from sqlalchemy.orm import Session
        from .database import SessionLocal # Your configured sessionmaker

        def get_db():
            db = SessionLocal() # 1. Create a new Session
            try:
                yield db # 2. Provide (yield) the session to the dependent
            finally:
                db.close() # 3. Ensure session is closed after use
        ```
    *   The `yield` passes the session to the route handler, and the `finally` block ensures cleanup happens even if errors occur.

3.  **FastAPI `Depends()`**:
    *   **Purpose:** This is FastAPI's mechanism for **dependency injection**. It tells FastAPI how to provide a required value (like a database session) to a route handler function.
    *   **Usage:**
        ```python
        # Example (in a router file, e.g., app/domains/accounts/router.py)
        from fastapi import Depends
        from sqlalchemy.orm import Session
        from app.db.base import get_db # Import the factory

        @router.get("/some-path")
        def my_route_handler(db: Session = Depends(get_db)):
            # FastAPI calls get_db() and passes the yielded session as 'db'
            # Use 'db' here to interact with the database, often via a service layer
            # ...
            return {"data": "..."}
        ```
    *   `db: Session = Depends(get_db)` declares that the function needs a `Session` named `db`, and FastAPI should call `get_db` to get it.

## Request Lifecycle Flow

1.  A request arrives at an endpoint (e.g., `/api/v1/accounts/`).
2.  FastAPI inspects the route handler function (e.g., `read_all_accounts`).
3.  It sees the parameter `db: Session = Depends(get_db)`.
4.  FastAPI calls the `get_db()` function.
5.  `get_db()` creates a new `Session` instance.
6.  `get_db()` `yield`s the session.
7.  FastAPI takes the yielded session and passes it as the `db` argument to the `read_all_accounts` function.
8.  The `read_all_accounts` function executes:
    *   It typically instantiates a service class (e.g., `AccountService(db)`), passing the session.
    *   The service uses the session (`self.db`) to perform database operations (queries, updates, etc.).
    *   The handler returns the results from the service.
9.  FastAPI sends the response back to the client.
10. FastAPI resumes the `get_db()` function after the `yield` statement.
11. The `finally` block in `get_db()` executes, calling `db.close()` to clean up the session and release the database connection.

## Why This Pattern?

*   **Decoupling:** Route handlers declare dependencies (`Depends(get_db)`) without knowing the implementation details of session management.
*   **Testability:** Dependencies can be easily overridden during testing (e.g., providing a session for a test database).
*   **Reusability & Maintainability:** Session logic is centralized in `get_db`.
*   **Clean Code:** Route handlers focus on application logic, not database setup/teardown boilerplate.
*   **Resource Management:** Ensures database sessions are reliably closed after each request. 