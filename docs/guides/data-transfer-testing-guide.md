# Data Transfer Testing Guide

## Overview
This guide provides step-by-step instructions for testing the Export and Import functionality of the Better Call Buffet financial data management system.

## Prerequisites

1. **Docker Running**: Ensure Docker daemon is running
2. **Database Running**: PostgreSQL container must be active
3. **API Server Running**: Application server must be running
4. **User Account**: You need a valid user account with financial data

## Starting the Application

```bash
# Start all services
docker compose up -d

# Check logs for any errors
docker compose logs -f web

# Verify API is running
curl http://localhost:8000/health
```

## Test Data Preparation

### Option 1: Use Existing Data
If you have existing financial data in your account, you can use it directly for export testing.

### Option 2: Seed Test Data
```bash
# Run database seeding script
docker compose exec web python scripts/seed_db.py
```

## Testing Export Functionality

### Test 1: Basic Export (All Data)

**Endpoint**: `POST /api/v1/data_transfer/export`

**Request**:
```bash
curl -X POST http://localhost:8000/api/v1/data_transfer/export \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "include_deleted": false,
    "format": "csv"
  }'
```

**Expected Response**:
```json
{
  "export_id": "abc-123-def-456",
  "status": "completed",
  "file_size": 1048576,
  "row_count": 1500,
  "download_url": "/api/v1/data_transfer/export/abc-123-def-456/download",
  "created_at": "2024-02-01T10:00:00",
  "completed_at": "2024-02-01T10:00:05"
}
```

**Verification**:
- ✅ Status is "completed"
- ✅ file_size > 0
- ✅ row_count matches expected transaction count
- ✅ download_url is provided

### Test 2: Export with Date Range Filter

**Request**:
```bash
curl -X POST http://localhost:8000/api/v1/data_transfer/export \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "date_from": "2024-01-01",
    "date_to": "2024-12-31",
    "include_deleted": false,
    "format": "csv"
  }'
```

**Verification**:
- ✅ Only transactions within date range are exported
- ✅ row_count is less than or equal to full export

### Test 3: Download Exported File

**Endpoint**: `GET /api/v1/data_transfer/export/{export_id}/download`

**Request**:
```bash
curl -X GET http://localhost:8000/api/v1/data_transfer/export/abc-123-def-456/download \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -o exported_data.csv
```

**Verification**:
- ✅ File downloads successfully
- ✅ File is valid CSV format
- ✅ File opens in spreadsheet application
- ✅ Headers match expected schema
- ✅ Data is human-readable (names, not UUIDs)

### Test 4: Verify CSV Content

Open the downloaded CSV file and verify:

**Required Columns**:
- transaction_date
- transaction_amount
- transaction_description
- transaction_movement_type

**Optional Columns** (if data exists):
- account_name
- credit_card_name
- category_name
- vendor_name
- broker_name

**Data Quality Checks**:
- ✅ Dates are in YYYY-MM-DD format
- ✅ Amounts are decimal numbers
- ✅ No UUID values visible (all replaced with names)
- ✅ Related entities show names, not IDs
- ✅ Parent categories referenced correctly
- ✅ Transfer transactions show both accounts

## Testing Import Functionality

### Test 5: Validate CSV Before Import

**Endpoint**: `POST /api/v1/data_transfer/import/validate`

**Request**:
```bash
curl -X POST http://localhost:8000/api/v1/data_transfer/import/validate \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -F "file=@exported_data.csv"
```

**Expected Response**:
```json
{
  "valid": true,
  "row_count": 1500,
  "estimated_entities": {
    "brokers": 3,
    "accounts": 5,
    "credit_cards": 3,
    "categories": 25,
    "vendors": 150,
    "transactions": 1500
  },
  "warnings": [],
  "errors": []
}
```

**Verification**:
- ✅ valid is true
- ✅ row_count matches CSV
- ✅ estimated_entities looks reasonable
- ✅ No errors reported

### Test 6: Basic Import (Validation Only)

**Endpoint**: `POST /api/v1/data_transfer/import`

**Request**:
```bash
curl -X POST "http://localhost:8000/api/v1/data_transfer/import?validate_only=true" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -F "file=@exported_data.csv"
```

**Verification**:
- ✅ Returns validation results
- ✅ No data actually imported
- ✅ Database unchanged

### Test 7: Full Import (New User Account)

**Setup**: Create a new test user account

**Request**:
```bash
curl -X POST "http://localhost:8000/api/v1/data_transfer/import?skip_errors=true" \
  -H "Authorization: Bearer NEW_USER_TOKEN_HERE" \
  -F "file=@exported_data.csv"
```

**Expected Response**:
```json
{
  "import_id": "xyz-789-abc-123",
  "status": "completed",
  "statistics": {
    "total_rows": 1500,
    "processed_rows": 1500,
    "skipped_rows": 0,
    "error_rows": 0
  },
  "entities_created": {
    "brokers": 3,
    "accounts": 5,
    "credit_cards": 3,
    "categories": 25,
    "vendors": 150,
    "subscriptions": 10,
    "installment_plans": 5,
    "installments": 0,
    "transactions": 1500
  },
  "errors": [],
  "warnings": []
}
```

**Verification**:
- ✅ Status is "completed"
- ✅ processed_rows equals total_rows
- ✅ Entities created match expectations
- ✅ No errors reported

### Test 8: Verify Imported Data

**Check Transactions**:
```bash
curl -X GET http://localhost:8000/api/v1/transactions \
  -H "Authorization: Bearer NEW_USER_TOKEN_HERE"
```

**Verification**:
- ✅ Transaction count matches import
- ✅ All relationships intact (accounts, categories, vendors)
- ✅ Dates preserved correctly
- ✅ Amounts match original data

**Check Accounts**:
```bash
curl -X GET http://localhost:8000/api/v1/accounts \
  -H "Authorization: Bearer NEW_USER_TOKEN_HERE"
```

**Verification**:
- ✅ All accounts created
- ✅ Account types correct
- ✅ Brokers associated correctly

**Check Categories**:
```bash
curl -X GET http://localhost:8000/api/v1/categories \
  -H "Authorization: Bearer NEW_USER_TOKEN_HERE"
```

**Verification**:
- ✅ Category hierarchy preserved
- ✅ Parent-child relationships correct

### Test 9: Duplicate Import (Same File Twice)

**Request**: Import the same file again to the same user

**Expected Behavior**:
- ✅ Append-only strategy: no updates to existing records
- ✅ Duplicate transactions skipped
- ✅ skipped_rows count reflects duplicates
- ✅ No new transactions created

### Test 10: Import with Errors

**Setup**: Create a CSV with intentional errors:
- Invalid date format
- Missing required fields
- Invalid movement type

**Request**:
```bash
curl -X POST "http://localhost:8000/api/v1/data_transfer/import?skip_errors=true" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -F "file=@invalid_data.csv"
```

**Verification**:
- ✅ Valid rows imported
- ✅ Invalid rows skipped
- ✅ Detailed error messages returned
- ✅ Database consistent (no partial imports)

## Edge Case Testing

### Test 11: Large File Import

**Setup**: Create or export a CSV with 10,000+ transactions

**Verification**:
- ✅ Import completes without timeout
- ✅ Memory usage acceptable
- ✅ All transactions imported correctly

### Test 12: Special Characters in Data

**Setup**: Create data with:
- Commas in descriptions
- Quotes in names
- Unicode characters
- Line breaks in text

**Verification**:
- ✅ CSV escaping correct
- ✅ Import handles special characters
- ✅ No data corruption

### Test 13: Empty/Minimal Data

**Setup**: Export from user with no transactions

**Verification**:
- ✅ Export returns CSV with headers only
- ✅ Import accepts empty file
- ✅ No errors reported

### Test 14: Transfer Transactions

**Setup**: Create transactions with from_account and to_account

**Verification**:
- ✅ Export includes both account names
- ✅ Import creates transfer correctly
- ✅ Movement type is "TRANSFER"

### Test 15: Hierarchical Categories

**Setup**: Transactions with parent and child categories

**Verification**:
- ✅ Export includes both category_name and category_parent
- ✅ Import creates parents before children
- ✅ Hierarchy preserved correctly

## Interactive Testing with Swagger UI

Access FastAPI's interactive documentation:

```
http://localhost:8000/docs
```

**Navigate to "data_transfer" section**:

1. Click "POST /data_transfer/export"
2. Click "Try it out"
3. Fill in request parameters
4. Click "Execute"
5. Review response

## Performance Benchmarks

Expected performance metrics:

| Operation | Data Size | Expected Time |
|-----------|-----------|---------------|
| Export | 1,000 transactions | < 2 seconds |
| Export | 10,000 transactions | < 10 seconds |
| Import | 1,000 transactions | < 5 seconds |
| Import | 10,000 transactions | < 30 seconds |

## Troubleshooting

### Export Issues

**Problem**: Export returns empty file
- Check: User has financial data
- Check: Date range filter isn't too restrictive
- Check: include_deleted setting

**Problem**: Export fails with 500 error
- Check: Database connection
- Check: Server logs for detailed error
- Check: Disk space for temporary files

### Import Issues

**Problem**: All rows skipped
- Cause: Duplicate data already exists
- Solution: Use different test user or modify CSV data

**Problem**: Import validation fails
- Cause: CSV format incorrect
- Solution: Check required columns
- Solution: Verify date and amount formats

**Problem**: Relationships not created
- Cause: Name matching failed
- Solution: Ensure consistent naming
- Solution: Check for typos in CSV

## Security Testing

### Test 16: Cross-User Access

**Setup**: User A exports data, User B tries to download

**Verification**:
- ✅ User B cannot access User A's export
- ✅ Returns 403 or 404 error

### Test 17: File Size Limit

**Setup**: Attempt to upload file > 50MB

**Verification**:
- ✅ Upload rejected
- ✅ Clear error message returned

### Test 18: Invalid File Types

**Setup**: Attempt to upload non-CSV file

**Verification**:
- ✅ Upload rejected
- ✅ Only .csv extension accepted

## Cleanup

After testing:

```bash
# Stop containers
docker compose down

# Clean up test data (if needed)
docker compose exec web python scripts/clean_test_data.py

# Remove temporary export files
rm -rf /tmp/data_exports/*
```

## Test Checklist

### Export Tests
- [ ] Basic export (all data)
- [ ] Export with date range filter
- [ ] Download exported file
- [ ] Verify CSV content structure
- [ ] Verify data quality

### Import Tests
- [ ] Validate CSV before import
- [ ] Import to new user account
- [ ] Verify imported transactions
- [ ] Verify imported accounts
- [ ] Verify imported categories
- [ ] Verify imported relationships
- [ ] Duplicate import handling
- [ ] Import with errors (skip_errors=true)
- [ ] Import with errors (skip_errors=false)

### Edge Cases
- [ ] Large file import (10k+ rows)
- [ ] Special characters handling
- [ ] Empty data export/import
- [ ] Transfer transactions
- [ ] Hierarchical categories
- [ ] Subscription data
- [ ] Installment plan data

### Security Tests
- [ ] Cross-user access prevention
- [ ] File size limit enforcement
- [ ] Invalid file type rejection
- [ ] SQL injection prevention
- [ ] CSV injection prevention

### Performance Tests
- [ ] Export timing benchmarks
- [ ] Import timing benchmarks
- [ ] Memory usage monitoring
- [ ] Concurrent operations

## Reporting Issues

When reporting issues, include:

1. Test case number
2. Request payload (sanitized)
3. Response received
4. Expected vs actual behavior
5. Server logs (if available)
6. Sample CSV file (if relevant)

## Success Criteria

All tests pass if:
- ✅ User can export all their financial data
- ✅ CSV file contains human-readable data
- ✅ User can import previously exported CSV
- ✅ All relationships preserved correctly
- ✅ No data loss during export/import cycle
- ✅ Duplicate detection works correctly
- ✅ Clear error messages for failures
- ✅ Performance meets benchmarks