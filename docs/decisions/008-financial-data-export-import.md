# ADR-008: Financial Data Export/Import Feature

## Status
Accepted

## Context
Users need the ability to:
1. Export their financial data for backup, analysis, or migration purposes
2. Import previously exported data to restore or migrate their financial information
3. Transfer data between accounts or to other systems

Current system state:
- All financial data is user-scoped with UUID primary keys
- Complex relationships exist between entities (accounts, transactions, categories, etc.)
- Data integrity depends on foreign key relationships
- Some entities have soft-delete flags

## Decision

### Export Feature (v1)
We will implement a CSV export feature with the following characteristics:

1. **Single CSV File Format**
   - All data in one CSV file with prefixed columns (e.g., `transaction_amount`, `account_name`)
   - Simpler for users to understand and manage
   - Easier to open in spreadsheet applications

2. **Name-Based References**
   - Replace all UUID foreign keys with human-readable names
   - Example: Instead of `account_id: "123e4567-e89b-12d3-a456-426614174000"`, use `account_name: "Checking Account"`
   - UUIDs that won't exist at import time (like user_id) are exported as null

3. **Active Records Only**
   - Export only active (non-deleted) records by default
   - Reduces file size and complexity
   - Avoids confusion with deleted data

4. **Comprehensive Data Scope**
   - Include: Transactions, Accounts, Credit Cards, Categories, Vendors, Brokers, Subscriptions, Installments
   - Exclude: Balance Points, Raw Invoices/Statements (JSON blobs), Refresh Tokens

### Import Feature (v2)
We will implement a CSV import feature with:

1. **Append-Only Strategy**
   - Never update existing records
   - Only add new records that don't already exist
   - Prevents accidental data overwrites
   - Uses name-based matching to detect duplicates

2. **Smart Entity Resolution**
   - Match entities by unique name combinations:
     - Accounts: name + broker
     - Credit Cards: name + account
     - Categories: name + parent
     - Vendors: name
   - Create missing entities automatically

3. **Dependency-Aware Import Order**
   - Create entities in correct order:
     1. Brokers
     2. Accounts
     3. Credit Cards
     4. Categories (parents first)
     5. Vendors
     6. Subscriptions
     7. Installment Plans & Installments
     8. Transactions

## Consequences

### Positive
- **User-Friendly**: Single CSV file is easy to understand and manage
- **Portability**: Name-based references make data human-readable
- **Safety**: Append-only prevents accidental data loss
- **Flexibility**: Users can edit CSV in spreadsheet applications
- **Compatibility**: CSV format works with many tools and systems

### Negative
- **No UUID Preservation**: Cannot maintain original IDs across export/import
- **Name Uniqueness Required**: Relies on unique names for entity matching
- **Potential Duplicates**: If users rename entities between export/import
- **Large File Size**: Single CSV might be large for users with many transactions
- **Limited Relationship Validation**: Cannot enforce all business rules in CSV

### Neutral
- **Performance**: CSV processing is memory-intensive for large datasets
- **Partial Imports**: Errors in one row don't affect others (could be positive or negative)
- **Manual Editing**: Users can modify CSV, which may cause import issues

## Alternatives Considered

1. **Multiple CSV Files (Rejected)**
   - One CSV per entity type in a ZIP file
   - More complex for users to manage
   - Better for maintaining relationships
   - Rejected for user simplicity

2. **JSON Format (Rejected)**
   - Preserves hierarchical relationships better
   - Can maintain UUIDs
   - Not user-editable in spreadsheets
   - Rejected for lack of user-friendliness

3. **Database Dump (Rejected)**
   - Perfect fidelity
   - Maintains all relationships and constraints
   - Not portable between systems
   - Not user-readable
   - Rejected for lack of portability

4. **Replace/Merge Strategy (Rejected)**
   - Update existing records on import
   - Risk of data corruption
   - Complex conflict resolution
   - Rejected for safety concerns

## Implementation Notes

### CSV Schema Design
```csv
transaction_date,transaction_amount,transaction_description,account_name,credit_card_name,category_name,vendor_name,...
2024-01-15,150.00,Grocery Shopping,Checking Account,,Food & Dining,Whole Foods,...
2024-01-16,2500.00,Rent Payment,Checking Account,,Housing,Landlord LLC,...
```

### Security Considerations
- File size limits (50MB max)
- Rate limiting on export/import endpoints
- Validate user ownership during export
- Sanitize CSV content during import
- Temporary file cleanup after download

### Error Handling
- Row-level error reporting during import
- Continue processing valid rows after errors
- Provide detailed error messages with row numbers
- Option to validate without importing

### Future Enhancements
- Scheduled automatic exports
- Cloud storage integration
- Incremental exports (date ranges)
- Export format options (JSON, Excel)
- Import conflict resolution strategies
- Bulk edit capabilities

## References
- [CSV RFC 4180](https://tools.ietf.org/html/rfc4180)
- [FastAPI File Uploads](https://fastapi.tiangolo.com/tutorial/request-files/)
- [Python CSV Module](https://docs.python.org/3/library/csv.html)

## Decision Date
2024-02-01

## Participants
- Development Team
- Product Owner
- End Users (via requirements)