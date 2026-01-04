# Plan: Cashflow Analytics Endpoint

## Phase 1: Structure & Definitions

### Goal

Create the `analytics` domain and define the data contract (Schema) for the cashflow endpoint.

### Tasks

- [ ] Create `app/domains/analytics` directory.
- [ ] Create `app/domains/analytics/__init__.py` (empty).
- [ ] Create `app/domains/analytics/schemas.py` defining `CashflowResponse`, `MonthlyCashflowData`, and `CashflowParams`.

## Phase 2: Data Access Layer (Repository)

### Goal

Implement the database query to aggregate transaction data by month.

### Tasks

- [ ] Create `app/domains/analytics/repository.py`.
- [ ] Implement `get_monthly_cashflow_stats(user_id, date_from, date_to, account_id)` using SQLAlchemy.
  - Use `func.date_trunc('month', Transaction.date)` for grouping.
  - Sum `amount` filtered by `movement_type`.
  - Handle `income`, `expense`, `investment`.
  - Calculate `savings` as `income - expenses` (net cashflow) for the monthly breakdown? Or just strictly aggregate columns.
    - _Decision_: The repository should return the raw aggregated sums. The Service will calculate `savings` and `net_cashflow`.

## Phase 3: Business Logic (Service)

### Goal

Process the raw data into the final response format.

### Tasks

- [ ] Create `app/domains/analytics/service.py`.
- [ ] Implement `get_cashflow_analytics`.
  - Call Repository.
  - Calculate `net_cashflow` = `total_income` - `total_expenses`.
  - Calculate `savings_rate` = `(net_cashflow / total_income) * 100`.
  - Format `monthly_data`.

## Phase 4: API & Integration

### Goal

Expose the endpoint and register/test it.

### Tasks

- [ ] Create `app/domains/analytics/router.py`.
  - Define `GET /cashflow`.
  - Use `Depends` for Authentication (`get_current_user`).
- [ ] Update `app/api/v1/__init__.py` to include `analytics` router.
- [ ] Verification: User manual review or run a curl command (if possible).

## Dependencies

- `Transaction` model (`app/domains/transactions/models.py`)
- `User` auth (`app/core/dependencies` likely)
