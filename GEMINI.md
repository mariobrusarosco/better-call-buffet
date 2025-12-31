# Context: Better Call Buffet

##  Project Overview
**Better Call Buffet** is a modern financial management and analysis platform built with **FastAPI**. It features domain-driven design, AI-powered insights (OpenAI/Ollama), and a professional-grade architecture (PostgreSQL, Docker, Railway).

**Key Technologies:**
- **Language:** Python 3.11+
- **Framework:** FastAPI
- **Database:** PostgreSQL (with SQLAlchemy 2.0 & Alembic)
- **Dependency Management:** Poetry (**Strictly enforced**)
- **Infrastructure:** Docker Compose (Local), Railway (Production)
- **AI:** OpenAI API, Ollama

### AI Agent Guidelines
* It's MANDATORY that you don't rush into fixes and implementations. Always ask for clarifications and ask for the context before proceeding. Only if the prompt is very specific about you fixing and coding right away, then proceed.
* Reason. Your goal is to provide the best possible code to the user, and to do that, you need to understand the context of the project and the user's needs.

#### Planner Mode
* Breakdown the feature into Phases and provide a clear plan of action.
* Breakdown Phases into small tasks and provide a clear plan of action.
* Consider break tasks into subtasks.
* Create a `.md` file for the plan. Store in the `/docs/plans` folder.
* Fprmat
```
# Phase 1

## Goal

## Tasks

### Task 1 - lorem ipsum dolor sit amet []
#### Task 1.1 - lorem ipsum dolor sit amet []
#### Task 1.2 - lorem ipsum dolor sit amet []

...


## Dependencies

## Expected Result

## Next Steps

```
* Once you finish a task, ask user to review your work. 
* Wait for user's confirmation before proceeding to the next task. 
* Be patient and don't rush into fixes and implementations.
* Be ready to do fixes.
* Once confirmed by the user, mark the current sub-task or task as done.
* If you need to do a fix, mark the current sub-task or task as in progress.

###  Educational Mode
This project is used for learning. When assisting:

1.  **Explain "Why"**: Don't just provide code. Explain the architectural decision (e.g., "We put this in the Repository layer because...").
2.  **Adhere to DDD**: Strictly respect domain boundaries. Do not cross-import repositories between domains if avoidable; use Services.
3.  **Safety**: Always check `git status` before big changes.
4.  **Documentation**: If creating a new architectural pattern, suggest creating an ADR in `docs/decisions/`.


##  Architecture: Domain-Driven Design
The project follows a **Clean Architecture** pattern organized by business domains.

### Directory Structure
```
app/
├── api/v1/                 # API Routing Layer (routes only)
├── core/                   # Config, Middleware, Error Handling
├── db/                     # DB Connection, Base Models
└── domains/                # Business Logic (DDD)
    ├── accounts/
    ├── balance_points/
    ├── transactions/
    └── [domain_name]/
        ├── models.py       # SQLAlchemy Database Models
        ├── schemas.py      # Pydantic Request/Response Models
        ├── service.py      # Business Logic
        ├── repository.py   # Data Access Layer
        └── router.py       # API Endpoints
```

### Layer Responsibilities
1.  **Router (`router.py`)**: Handles HTTP concerns, request parsing, and status codes. Calls the Service. Returns **Schemas**.
2.  **Service (`service.py`)**: Contains business logic, validation, and AI integration. Calls the Repository. Returns **Models**.
3.  **Repository (`repository.py`)**: Handles raw database queries and persistence. Returns **Models**.
4.  **Models (`models.py`)**: SQLAlchemy definitions (DB Tables).
5.  **Schemas (`schemas.py`)**: Pydantic definitions (API Contracts).

##  Development Workflow (CRITICAL)

### 🐳 Docker First
**Always** use Docker Compose for local development. The environment is containerized to ensure consistency.

### 📦 Dependency Management (Poetry)
**NEVER** use `pip install`. **ALWAYS** use `poetry`.
Since the app runs in Docker, dependencies must be managed there:

*   **Add Dependency:** `docker compose exec web poetry add <package>`
*   **Add Dev Dependency:** `docker compose exec web poetry add --group dev <package>`
*   **Update Lockfile:** `docker compose exec web poetry lock`
*   **Rebuild:** After adding dependencies, run `docker compose up --build`.

##  Essential Commands

| Action | Command |
| :--- | :--- |
| **Start App** | `docker compose up` |
| **Stop App** | `docker compose down` |
| **Run Tests** | `docker compose exec web poetry run pytest` |
| **Format Code** | `docker compose exec web poetry run black .` |
| **Type Check** | `docker compose exec web poetry run mypy app` |
| **Make Migration** | `docker compose exec web alembic revision --autogenerate -m "desc"` |
| **Apply Migration** | `docker compose exec web alembic upgrade head` |
| **Seed DB** | `docker compose exec web python scripts/seed_db.py` |

##  Coding Standards

*   **File Naming**: Use `kebab-case` for files (e.g., `user-categories.md`) but standard Python `snake_case` for modules.
*   **Pydantic Naming**:
    *   `{Domain}Create` (POST requests)
    *   `{Domain}Update` (PATCH requests)
    *   `{Domain}Response` (Single outputs)
    *   `{Domain}ListResponse` (Paginated outputs)
*   **Imports**: Use absolute imports (e.g., `from app.core.config import settings`).

