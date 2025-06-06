# API Routing Documentation

## Overview

Better Call Buffet uses a structured API routing system built with FastAPI. All API endpoints are organized under domains following a RESTful design approach. The base API path is `/api/v1/`, followed by domain-specific resources.

## API Structure

```
/api/v1
├── /users           # User management
├── /accounts        # Financial accounts
├── /categories      # Transaction categories
└── /transactions    # Financial transactions
```

## Authentication

**Note:** Authentication is currently implemented as a placeholder with a `user_id` parameter. 
Future implementation will use JWT-based authentication with bearer tokens.

## API Domains

### Users API

**Base path:** `/api/v1/users`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST   | `/`      | Create a new user |
| GET    | `/me`    | Get current user information |

### Accounts API

**Base path:** `/api/v1/accounts`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST   | `/`      | Create a new account |
| GET    | `/`      | List all accounts for the current user |
| GET    | `/active`| List active accounts for the current user |
| GET    | `/balance/total` | Get total balance across all active accounts |
| GET    | `/{account_id}` | Get a specific account by ID |
| PUT    | `/{account_id}` | Update an account |
| DELETE | `/{account_id}` | Delete an account |
| PATCH  | `/{account_id}/deactivate` | Deactivate an account |

#### Request Parameters

- **List accounts**
  - `skip`: Number of records to skip (pagination)
  - `limit`: Maximum number of records to return (pagination)
  
- **Get total balance**
  - `currency`: Currency code (default: USD)

### Categories API

**Base path:** `/api/v1/categories`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST   | `/`      | Create a new category |
| GET    | `/`      | List all categories for the current user |
| GET    | `/active`| List active categories for the current user |
| GET    | `/hierarchy` | Get hierarchical category structure |
| GET    | `/type/{category_type}` | Get categories by type (income or expense) |
| GET    | `/{category_id}` | Get a specific category by ID |
| PUT    | `/{category_id}` | Update a category |
| DELETE | `/{category_id}` | Delete a category |
| PATCH  | `/{category_id}/deactivate` | Deactivate a category |
| POST   | `/defaults` | Create default categories for the current user |

#### Request Parameters

- **List categories**
  - `skip`: Number of records to skip (pagination)
  - `limit`: Maximum number of records to return (pagination)

- **Get categories by type**
  - `category_type`: Either "income" or "expense"

### Transactions API

**Base path:** `/api/v1/transactions`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST   | `/`      | Create a new transaction |
| POST   | `/with-recurrence` | Create a transaction with recurrence |
| GET    | `/`      | List transactions with filtering options |
| GET    | `/summary/by-category` | Get transaction summary grouped by category |
| GET    | `/summary/monthly/{year}` | Get monthly summaries for an entire year |
| GET    | `/summary/monthly/{year}/{month}` | Get transaction summary for a specific month |
| GET    | `/{transaction_id}` | Get a specific transaction by ID |
| PUT    | `/{transaction_id}` | Update a transaction |
| DELETE | `/{transaction_id}` | Delete a transaction |

#### Request Parameters

- **List transactions**
  - `skip`: Number of records to skip (pagination)
  - `limit`: Maximum number of records to return (pagination)
  - `start_date`: Filter by start date
  - `end_date`: Filter by end date
  - `transaction_type`: Filter by type (income, expense, transfer)
  - `category_id`: Filter by category
  - `account_id`: Filter by account

- **Get transaction summary by category**
  - `start_date`: Start date for the summary period
  - `end_date`: End date for the summary period
  - `transaction_type`: Type of transactions to include (income or expense)

- **Get monthly summary**
  - `year`: Year for the summary
  - `month`: Month for the summary (optional, if omitted returns all months)

## Data Models

### Account Types
- `checking`
- `savings`
- `credit`
- `cash`
- `investment`
- `other`

### Category Types
- `income`
- `expense`

### Transaction Types
- `income`
- `expense`
- `transfer`

### Recurrence Frequencies
- `daily`
- `weekly`
- `biweekly`
- `monthly`
- `quarterly`
- `yearly`

## Error Responses

All API endpoints follow a consistent error response format:

```json
{
  "detail": "Error message describing the issue"
}
```

Common HTTP status codes:
- `400 Bad Request`: Invalid data or parameters
- `403 Forbidden`: Not enough permissions
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server-side error

## Future API Endpoints

The following domains are planned for future implementation:

### Budgets API

**Base path:** `/api/v1/budgets`

### Reports API

**Base path:** `/api/v1/reports`

### AI Insights API

**Base path:** `/api/v1/insights` 