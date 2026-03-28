# Plan: User Data Export Feature

## Goal
Enable users to export all their personal data from the application in a portable JSON format. This ensures data sovereignty and allows users to backup or analyze their data externally.

## Phases

### Phase 1: Architecture & Core Implementation
**Goal:** Create the `data_export` domain and implement the orchestration logic to gather data from various domains.

#### Tasks
- [ ] **Task 1.1:** Initialize `data_export` domain structure (`app/domains/data_export`).
- [ ] **Task 1.2:** Define Pydantic models (`schemas.py`) for the export structure.
    - **Structure:**
        ```python
        class UserDataExport(BaseModel):
            user: UserResponse
            accounts: List[AccountResponse]
            transactions: List[TransactionResponse]
            categories: List[CategoryResponse]
            subscriptions: List[SubscriptionResponse]
            installments: List[InstallmentPlanResponse]
            vendors: List[VendorResponse]
            credit_cards: List[CreditCardResponse]
            exported_at: datetime
            version: str = "1.0"
        ```
- [ ] **Task 1.3:** Implement `DataExportService` to aggregate data.
    - **Dependency Injection:** Inject Services/Repositories from: `users`, `accounts`, `transactions`, `categories`, `subscriptions`, `installments`, `vendors`, `credit_cards`.
    - **Logic:**
        1. Fetch `User` data.
        2. Fetch all `Accounts` (using `get_all_by_user`).
        3. Fetch all `Transactions` (using `get_multi` with a large limit or a new `get_all_iterator`).
        4. Fetch all `Categories`, `Subscriptions`, `Installments`, `Vendors`, `CreditCards`.
        5. Assemble into the `UserDataExport` schema.
- [ ] **Task 1.4:** Register the new domain in `app/api/v1/__init__.py`.

### Phase 2: API & Integration
**Goal:** Expose the functionality via an HTTP endpoint.

#### Tasks
- [ ] **Task 2.1:** Create `router.py` in `data_export` with `GET /json` endpoint.
    - **Endpoint:** `GET /api/v1/data-export/json` (or `/export/json` mounted under a group).
    - **Response:** `UserDataExport`
- [ ] **Task 2.2:** Verify permissions (current user only).
- [ ] **Task 2.3:** Wire up `api_router` to include `data_export`.

### Phase 3: Testing & Verification
**Goal:** Ensure data is complete and format is correct.

#### Tasks
- [ ] **Task 3.1:** Add unit test for `DataExportService`.
    - Mock all dependent services.
    - Verify that the output matches the expected schema.
- [ ] **Task 3.2:** Add integration test for the API endpoint.
    - Create dummy data (User, Account, Transaction).
    - Call the endpoint.
    - Verify the JSON response contains the created data.
- [ ] **Task 3.3:** Manual verification via Swagger UI.

## Dependencies
- Existing domains (`users`, `accounts`, `transactions`, `categories`, `subscriptions`, `installments`, `vendors`, `credit_cards`) need to be accessible.
- We will rely on existing `get_multi` methods or `Repositories` where appropriate.

## Expected Result
- A new endpoint `GET /api/v1/data-export/json` that returns a structured JSON object containing all user data.
