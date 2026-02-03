# Export/Import Financial Data Implementation Plan

## Overview
Create a new **data_transfer** domain to handle export and import of financial data as CSV files, following the existing Domain-Driven Design architecture.

## User Requirements Summary
Based on user feedback:
- **CSV Structure**: Single CSV file with prefixed columns
- **Export Scope**: Core Financial Data + Recurring Data + Metadata (excluding historical data like balance points)
- **Deleted Records**: Export active records only
- **Import Strategy**: Append-only (add new records, skip conflicts)

## Phase 1: Documentation & Design (30 mins)

### 1.1 Create ADR (Architectural Decision Record)
- **File**: `docs/decisions/008-financial-data-export-import.md`
- Document why we chose:
  - Single CSV format with prefixed columns
  - Append-only import strategy
  - Exclusion of UUIDs that won't exist at import time
  - Active records only for export

### 1.2 Create Domain Guide
- **File**: `docs/domains/data-transfer.md`
- Document the export/import flow, CSV schema, and data mapping

### 1.3 Create Implementation Guide
- **File**: `docs/guides/export-import-strategy.md`
- Detail the technical implementation approach

## Phase 2: v1 - Export Feature Implementation (2-3 hours)

### 2.1 Create Data Transfer Domain Structure
```
app/domains/data_transfer/
├── __init__.py
├── models.py        # Export/Import job tracking (optional)
├── schemas.py       # Request/Response models
├── service.py       # Export/Import business logic
├── repository.py    # Data access for export/import
├── router.py        # API endpoints
└── csv_handler.py   # CSV generation/parsing utilities
```

### 2.2 Define CSV Schema & Mapping

**CSV Columns Structure** (single file with prefixed columns):
- Transaction columns: `transaction_id`, `transaction_date`, `transaction_amount`, `transaction_description`, `transaction_movement_type`, `transaction_category`, `transaction_is_paid`
- Account columns: `account_name`, `account_type`, `account_currency`, `account_broker`
- Credit Card columns: `credit_card_name`, `credit_card_brand`, `credit_card_last_four`, `credit_card_limit`
- Category columns: `category_name`, `category_parent`
- Vendor columns: `vendor_name`, `vendor_website`
- Subscription columns: `subscription_name`, `subscription_amount`, `subscription_billing_cycle`, `subscription_next_due_date`
- Installment columns: `installment_plan_name`, `installment_number`, `installment_total_amount`, `installment_count`

### 2.3 Implement Export Service

**Export Logic**:
1. Fetch all active user data (exclude soft-deleted)
2. Build relationships map in memory
3. Flatten hierarchical data into CSV rows
4. Replace UUIDs with human-readable references:
   - user_id → null (will be set on import)
   - account_id → account_name
   - credit_card_id → credit_card_name
   - category_id → category_name
   - vendor_id → vendor_name
5. Generate CSV with proper escaping and encoding

### 2.4 Create Export API Endpoints

**Endpoints**:
- `POST /api/v1/data_transfer/export` - Trigger export for authenticated user
- `GET /api/v1/data_transfer/export/{export_id}/download` - Download generated CSV

**Features**:
- Optional date range filter
- Progress tracking for large exports
- Temporary file storage with cleanup

## Phase 3: v2 - Import Feature Implementation (3-4 hours)

### 3.1 Implement CSV Parser

**Parsing Strategy**:
1. Validate CSV structure and headers
2. Parse rows into intermediate objects
3. Validate data types and required fields
4. Build entity creation order based on dependencies

### 3.2 Implement Import Service

**Import Logic**:
1. Parse uploaded CSV file
2. Extract and validate all entities
3. Create entities in dependency order:
   - Brokers (by name, skip if exists)
   - Accounts (by name + broker, skip if exists)
   - Credit Cards (by name + account, skip if exists)
   - Categories (parent first, then children, skip if exists)
   - Vendors (by name, skip if exists)
   - Subscriptions (link to vendor/category by name)
   - Installment Plans & Installments
   - Transactions (link to all related entities by name)
4. Handle relationships by name matching
5. Set user_id from authenticated user
6. Apply append-only strategy (skip existing records)

### 3.3 Create Import API Endpoints

**Endpoints**:
- `POST /api/v1/data_transfer/import` - Upload CSV and start import
- `GET /api/v1/data_transfer/import/{import_id}/status` - Check import progress
- `POST /api/v1/data_transfer/import/validate` - Validate CSV without importing

**Features**:
- File size limits
- Validation-only mode
- Import progress tracking
- Error reporting with row numbers
- Rollback on critical errors

## Phase 4: Testing & Validation (1 hour)

### 4.1 Create Test Data
- Generate sample exports with various data scenarios
- Test edge cases (empty categories, orphaned transactions)

### 4.2 End-to-End Testing
- Export user data → Download CSV → Import to new user
- Verify data integrity and relationships

### 4.3 Performance Testing
- Test with large datasets (10k+ transactions)
- Optimize query performance if needed

## Phase 5: Error Handling & Edge Cases (1 hour)

### 5.1 Handle Edge Cases
- Circular references in categories
- Missing related entities during import
- Duplicate detection (by name + key fields)
- Invalid date formats or amounts
- Character encoding issues

### 5.2 Add Comprehensive Logging
- Log each import/export phase
- Track entity creation counts
- Record any data transformations

## Technical Implementation Details

### Key Design Decisions:

1. **No UUID Preservation**: Replace all UUIDs with name-based references that can be resolved on import
2. **Name-Based Matching**: Use unique combinations (e.g., account_name + broker_name) for entity resolution
3. **Append-Only Import**: Never update existing records, only add new ones
4. **Single CSV Format**: All data in one file for simplicity
5. **Active Records Only**: Exclude soft-deleted records from export

### Data Mapping Strategy:

**Export Transformations**:
- transaction.account_id → account.name
- transaction.credit_card_id → credit_card.name
- transaction.category_id → category.name
- transaction.vendor_id → vendor.name
- All user_id fields → null

**Import Transformations**:
- account.name → lookup account_id (create if not exists)
- credit_card.name → lookup credit_card_id (create if not exists)
- category.name → lookup category_id (create if not exists)
- vendor.name → lookup vendor_id (create if not exists)
- null user_id → current authenticated user's ID

### Security Considerations:
- Validate user ownership during export
- Sanitize file uploads during import
- Rate limiting on export/import endpoints
- File size limits (e.g., max 50MB)
- Temporary file cleanup after download

## Migration Strategy
No database migrations needed - this feature uses existing models

## Estimated Timeline
- **Phase 1**: 30 minutes (Documentation)
- **Phase 2**: 2-3 hours (Export - v1)
- **Phase 3**: 3-4 hours (Import - v2)
- **Phase 4**: 1 hour (Testing)
- **Phase 5**: 1 hour (Error handling)
- **Total**: 8-10 hours

## Success Criteria
✅ User can export all their financial data as a single CSV file
✅ CSV contains human-readable references (names, not UUIDs)
✅ User can import a previously exported CSV
✅ Import correctly recreates all relationships
✅ No data loss or duplication during export/import cycle
✅ Clear error messages for validation failures
✅ Performance acceptable for typical user data volumes

## Implementation Checklist

- [ ] Phase 1: Documentation
  - [ ] Create ADR document
  - [ ] Create domain guide
  - [ ] Create implementation strategy guide

- [ ] Phase 2: Export Feature (v1)
  - [ ] Create domain structure
  - [ ] Implement CSV handler
  - [ ] Create schemas
  - [ ] Implement repository layer
  - [ ] Implement service layer
  - [ ] Create API endpoints
  - [ ] Test export functionality

- [ ] Phase 3: Import Feature (v2)
  - [ ] Implement CSV parser
  - [ ] Implement import validation
  - [ ] Implement import service
  - [ ] Create import endpoints
  - [ ] Test import functionality

- [ ] Phase 4: Testing
  - [ ] Unit tests for CSV handler
  - [ ] Integration tests for export
  - [ ] Integration tests for import
  - [ ] End-to-end testing

- [ ] Phase 5: Polish
  - [ ] Error handling improvements
  - [ ] Performance optimization
  - [ ] Documentation updates
  - [ ] Code review and cleanup