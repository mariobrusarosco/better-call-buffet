# Phase 1: Domain Scaffolding & Models

## Goal
Create the foundational data structure for the Installments domain to support "Parcelamento" logic.

## Tasks

### Task 1 - Domain Structure [x]
#### Task 1.1 - Create directory `app/domains/installments/` [x]
#### Task 1.2 - Create `__init__.py` [x]

### Task 2 - Database Models [x]
#### Task 2.1 - Define `InstallmentPlan` (Parent) model in `models.py` [x]
#### Task 2.2 - Define `Installment` (Child) model in `models.py` [x]
#### Task 2.3 - Update `Transaction` model to include foreign keys [x]
#### Task 2.4 - Register new models in `app/db/model_registration.py` [x]

### Task 3 - Database Migration [x]
#### Task 3.1 - Generate Alembic migration (autogenerate) [x]
#### Task 3.2 - Review migration file [x]
#### Task 3.3 - Apply migration [x]

## Dependencies
- Existing `Vendor`, `UserCategory`, and `CreditCard` models.

## Expected Result
- Database tables `installment_plans` and `installments` created.
- `transactions` table updated with linking columns.

## Next Steps
- Phase 2: API Contracts & Data Access.

# Phase 2: API Contracts & Data Access

## Goal
Define Pydantic schemas for the API and implement the Repository layer for database interactions.

## Tasks

### Task 1 - Pydantic Schemas [x]
#### Task 1.1 - Define `InstallmentPlanCreate`, `InstallmentPlanUpdate` [x]
#### Task 1.2 - Define `InstallmentPlanResponse`, `InstallmentResponse` [x]
#### Task 1.3 - Define `InstallmentFilters` for pagination and searching [x]

### Task 2 - Repository Layer [~]
#### Task 2.1 - Implement `InstallmentRepository` with CRUD for Plans and individual Installments [x]
#### Task 2.2 - Add specialized queries (e.g., `get_by_plan_id`, `get_active_plans`) [x]

## Dependencies
- Phase 1 database models.

## Expected Result
- Type-safe schemas for request/response.
- Repository ready to be used by the Service layer.

## Next Steps
- Phase 3: Business Logic & Series Generation.

# Phase 3: Business Logic & Series Generation

## Goal
Implement the service logic to automatically generate the full series of installment records when a plan is created.

## Tasks

### Task 1 - Generation Engine [ ]
#### Task 1.1 - Implement `_generate_installments` helper (math for split, handling rounding remainders) [ ]
#### Task 1.2 - Implement date rollover logic (e.g., Jan 31 -> Feb 28) using existing utils [ ]

### Task 2 - Service Layer [ ]
#### Task 2.1 - Implement `InstallmentService.create_plan` (Atomic creation of Plan + $N$ Installments) [ ]
#### Task 2.2 - Implement ownership validation for `vendor`, `category`, and `credit_card` [ ]

## Dependencies
- Phase 2 schemas and repository.

## Expected Result
- Creating one Plan correctly generates all future occurrences in the database.

## Next Steps
- Phase 4: API Integration & Linking.

# Phase 4: API Integration & Linking

## Goal
Expose the installments management to the frontend and implement the reconciliation (linking) logic.

## Tasks

### Task 1 - API Router [ ]
#### Task 1.1 - Implement CRUD endpoints for `InstallmentPlan` [ ]
#### Task 1.2 - Implement list endpoints with pagination [ ]

### Task 2 - Reconciliation Logic [ ]
#### Task 2.1 - Implement `link_transaction` endpoint [ ]
#### Task 2.2 - Logic: Find `Transaction` -> Update `installment_id` -> Mark `Installment` as `LINKED` [ ]

## Dependencies
- Phase 3 service logic.

## Expected Result
- Functional API for managing installments and linking them to real transactions.

## Next Steps
- Phase 5: Forecast Integration.

# Phase 5: Forecast Integration

## Goal
Integrate installment projections into the unified "Forecast" view.

## Tasks

### Task 1 - Data Aggregation [ ]
#### Task 1.1 - Implement `get_upcoming_installments` in service [ ]
#### Task 1.2 - Ensure output matches the `UpcomingPaymentResponse` format [ ]

## Expected Result
- Future installments appear alongside subscriptions in the cash flow forecast.