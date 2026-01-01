# Plan: User Data Import Feature

## Goal
Enable users to restore or migrate their data into the application from a previously exported JSON file. This supports backup restoration and migrating between environments.

## Phases

### Phase 1: Architecture & Validation Logic
**Goal:** Create the import logic within the `data_export` domain (or rename to `data_portability`?) to handle parsing and validation.

#### Tasks
- [ ] **Task 1.1:** Define `ImportRequest` schema (accepts the JSON structure from Export).
- [ ] **Task 1.2:** Implement `DataImportService`.
    - **Strategy:** "Upsert" (Insert or Update) based on UUID.
    - **Order of Operations (Critical for Foreign Keys):**
        1. User (update self if matches, or error if trying to import another user's data?) -> *Decision: Only import data FOR the current logged-in user. Re-map `user_id` in all records to the current user to prevent ID collisions/security issues.*
        2. Categories & Vendors (Independent)
        3. Accounts (Independent)
        4. Credit Cards (Depends on Accounts)
        5. Subscriptions & Installments (Depend on Vendors/Categories/Accounts)
        6. Transactions (Depend on everything)
- [ ] **Task 1.3:** Implement `IdMappingService` (Optional but recommended).
    - If we want to strictly import *as new*, we generate new UUIDs and map old->new.
    - *Decision for V1:* Keep UUIDs if possible. If a record with that UUID exists, update it. If not, insert it. **Crucial:** Ensure `user_id` is overwritten to the current user's ID to prevent data leakage.

### Phase 2: Implementation of Import Logic
**Goal:** Write the service methods to persist the data.

#### Tasks
- [ ] **Task 2.1:** Implement `import_categories` and `import_vendors`.
- [ ] **Task 2.2:** Implement `import_accounts` and `credit_cards`.
- [ ] **Task 2.3:** Implement `import_subscriptions` and `installments`.
- [ ] **Task 2.4:** Implement `import_transactions` (Bulk insert for performance).
- [ ] **Task 2.5:** Wrap everything in a **Database Transaction**. If any part fails, rollback everything.

### Phase 3: API & Integration
**Goal:** Expose the import functionality.

#### Tasks
- [ ] **Task 3.1:** Create `POST /import/json` endpoint.
    - Input: JSON file upload or raw JSON body.
- [ ] **Task 3.2:** Add proper error handling (e.g., "Missing dependency for Transaction X").

### Phase 4: Testing
**Goal:** Verify data integrity after import.

#### Tasks
- [ ] **Task 4.1:** Test "Round Trip": Export -> Delete Data -> Import -> Verify Data matches.
- [ ] **Task 4.2:** Test "Merge": Import data into an account that already has some data.

## Dependencies
- All domains must allow "Upsert" or creating with specific UUIDs.
- `DataExportService` (for the schema definition).

## Expected Result
- A `POST /api/v1/data-export/import` (or similar) endpoint that accepts the JSON export and restores the state.
