# Financial Data Export/Import Strategy Guide

## Overview
This guide provides detailed technical implementation strategies for the financial data export/import feature. It covers data transformation, relationship handling, and edge case management.

## Export Strategy

### Data Transformation Pipeline

#### 1. Data Collection Phase
```python
# Pseudo-code for data collection
def collect_user_data(user_id: UUID) -> DataCollection:
    # Fetch all entities in parallel for performance
    brokers = fetch_brokers(user_id)
    accounts = fetch_accounts(user_id)
    credit_cards = fetch_credit_cards(user_id)
    categories = fetch_categories(user_id)
    vendors = fetch_vendors(user_id)
    subscriptions = fetch_subscriptions(user_id)
    installments = fetch_installments(user_id)
    transactions = fetch_transactions(user_id)

    return DataCollection(
        brokers=brokers,
        accounts=accounts,
        # ... etc
    )
```

#### 2. Relationship Mapping
Create lookup dictionaries for efficient UUID → Name resolution:

```python
# Build lookup maps
broker_map = {broker.id: broker.name for broker in brokers}
account_map = {account.id: account.name for account in accounts}
credit_card_map = {card.id: card.name for card in credit_cards}
category_map = {cat.id: cat.name for cat in categories}
vendor_map = {vendor.id: vendor.name for vendor in vendors}

# Handle parent categories
parent_category_map = {
    cat.id: category_map.get(cat.parent_id)
    for cat in categories
    if cat.parent_id
}
```

#### 3. CSV Row Generation
Transform each transaction into a CSV row:

```python
def transaction_to_csv_row(transaction, lookups):
    return {
        # Transaction fields
        'transaction_date': transaction.date.isoformat(),
        'transaction_amount': str(transaction.amount),
        'transaction_description': transaction.description,
        'transaction_movement_type': transaction.movement_type,
        'transaction_is_paid': str(transaction.is_paid),

        # Related entities by name
        'account_name': lookups.account_map.get(transaction.account_id),
        'credit_card_name': lookups.credit_card_map.get(transaction.credit_card_id),
        'category_name': lookups.category_map.get(transaction.category_id),
        'vendor_name': lookups.vendor_map.get(transaction.vendor_id),

        # Handle transfers
        'from_account_name': lookups.account_map.get(transaction.from_account_id),
        'to_account_name': lookups.account_map.get(transaction.to_account_id),

        # Subscription and installment data
        'subscription_name': lookups.subscription_map.get(transaction.subscription_id),
        'installment_number': get_installment_number(transaction.installment_id),
    }
```

### Handling Special Cases

#### 1. Orphaned Transactions
Transactions without accounts/credit cards (shouldn't happen, but handle gracefully):
```python
if not transaction.account_id and not transaction.credit_card_id:
    # Log warning but include in export
    logger.warning(f"Orphaned transaction: {transaction.id}")
    row['account_name'] = 'UNKNOWN_ACCOUNT'
```

#### 2. Deleted References
When referenced entity is deleted but transaction remains:
```python
# Fetch including deleted for complete picture
account = fetch_account(transaction.account_id, include_deleted=True)
if account and account.is_deleted:
    row['account_name'] = f"{account.name} (DELETED)"
```

#### 3. Transfer Transactions
Special handling for transfers between accounts:
```python
if transaction.from_account_id and transaction.to_account_id:
    row['transaction_movement_type'] = 'TRANSFER'
    row['from_account_name'] = lookups.account_map.get(transaction.from_account_id)
    row['to_account_name'] = lookups.account_map.get(transaction.to_account_id)
```

## Import Strategy

### Data Parsing Pipeline

#### 1. CSV Validation
```python
REQUIRED_HEADERS = [
    'transaction_date',
    'transaction_amount',
    'transaction_description',
    'transaction_movement_type'
]

OPTIONAL_HEADERS = [
    'account_name',
    'credit_card_name',
    'category_name',
    'vendor_name',
    # ... etc
]

def validate_csv_structure(headers):
    missing = set(REQUIRED_HEADERS) - set(headers)
    if missing:
        raise ValidationError(f"Missing required columns: {missing}")

    unknown = set(headers) - set(REQUIRED_HEADERS + OPTIONAL_HEADERS)
    if unknown:
        logger.warning(f"Unknown columns will be ignored: {unknown}")
```

#### 2. Entity Extraction
Extract unique entities from all rows:

```python
def extract_entities(rows):
    entities = {
        'brokers': set(),
        'accounts': set(),
        'credit_cards': set(),
        'categories': set(),
        'vendors': set(),
        'subscriptions': set()
    }

    for row in rows:
        if row.get('broker_name'):
            entities['brokers'].add(row['broker_name'])

        if row.get('account_name') and row.get('broker_name'):
            entities['accounts'].add((row['account_name'], row['broker_name']))

        # Extract parent categories first
        if row.get('category_parent'):
            entities['categories'].add((row['category_parent'], None))

        # Then child categories
        if row.get('category_name'):
            parent = row.get('category_parent')
            entities['categories'].add((row['category_name'], parent))

        # ... etc for other entities

    return entities
```

#### 3. Entity Creation Order
```python
async def create_entities_in_order(entities, user_id, db_session):
    created = {
        'brokers': {},
        'accounts': {},
        'credit_cards': {},
        'categories': {},
        'vendors': {},
        'subscriptions': {}
    }

    # 1. Create Brokers
    for broker_name in entities['brokers']:
        broker = await find_or_create_broker(
            name=broker_name,
            user_id=user_id,
            session=db_session
        )
        created['brokers'][broker_name] = broker.id

    # 2. Create Accounts (depends on Brokers)
    for account_name, broker_name in entities['accounts']:
        broker_id = created['brokers'].get(broker_name)
        if not broker_id:
            logger.warning(f"Broker not found for account: {account_name}")
            continue

        account = await find_or_create_account(
            name=account_name,
            broker_id=broker_id,
            user_id=user_id,
            session=db_session
        )
        created['accounts'][(account_name, broker_name)] = account.id

    # 3. Create Categories (handle hierarchy)
    # First pass: parent categories
    for cat_name, parent_name in entities['categories']:
        if parent_name is None:  # Parent category
            category = await find_or_create_category(
                name=cat_name,
                parent_id=None,
                user_id=user_id,
                session=db_session
            )
            created['categories'][cat_name] = category.id

    # Second pass: child categories
    for cat_name, parent_name in entities['categories']:
        if parent_name is not None:  # Child category
            parent_id = created['categories'].get(parent_name)
            category = await find_or_create_category(
                name=cat_name,
                parent_id=parent_id,
                user_id=user_id,
                session=db_session
            )
            created['categories'][cat_name] = category.id

    return created
```

### Duplicate Detection Strategy

#### 1. Broker Duplicate Detection
```python
async def find_or_create_broker(name, user_id, session):
    # Check if broker with same name exists for user
    existing = await session.query(Broker).filter(
        Broker.user_id == user_id,
        Broker.name == name,
        Broker.is_active == True
    ).first()

    if existing:
        return existing

    # Create new broker
    broker = Broker(
        id=uuid.uuid4(),
        user_id=user_id,
        name=name,
        is_active=True
    )
    session.add(broker)
    return broker
```

#### 2. Transaction Duplicate Detection
```python
async def is_duplicate_transaction(transaction_data, user_id, session):
    # Check for exact match on key fields
    existing = await session.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.date == transaction_data['date'],
        Transaction.amount == transaction_data['amount'],
        Transaction.description == transaction_data['description'],
        Transaction.is_deleted == False
    ).first()

    return existing is not None
```

### Error Recovery

#### 1. Transaction Rollback
```python
async def import_with_rollback(csv_file, user_id, session):
    try:
        # Start transaction
        async with session.begin():
            results = await process_import(csv_file, user_id, session)

            # Validate results
            if results.error_count > results.success_count * 0.1:  # >10% errors
                raise ImportError("Too many errors, rolling back")

            # Commit if successful
            await session.commit()
            return results

    except Exception as e:
        # Automatic rollback
        logger.error(f"Import failed, rolling back: {e}")
        await session.rollback()
        raise
```

#### 2. Partial Import Recovery
```python
class ImportCheckpoint:
    def __init__(self):
        self.processed_rows = set()
        self.created_entities = {}

    def save(self, row_number, entity_type, entity_id):
        self.processed_rows.add(row_number)
        self.created_entities[f"{entity_type}:{entity_id}"] = True

    def should_skip(self, row_number):
        return row_number in self.processed_rows

# Use checkpoint for resumable imports
checkpoint = ImportCheckpoint()
for i, row in enumerate(csv_rows):
    if checkpoint.should_skip(i):
        continue

    try:
        result = process_row(row)
        checkpoint.save(i, result.entity_type, result.entity_id)
    except Exception as e:
        logger.error(f"Row {i} failed: {e}")
        # Continue with next row
```

## Data Validation Rules

### Field Validations

#### 1. Amount Validation
```python
def validate_amount(amount_str):
    try:
        amount = Decimal(amount_str)
        # Check range
        if abs(amount) > Decimal('9999999999999.99'):
            raise ValidationError("Amount exceeds maximum")
        # Check precision
        if amount.as_tuple().exponent < -2:
            raise ValidationError("Too many decimal places")
        return amount
    except (InvalidOperation, ValueError):
        raise ValidationError(f"Invalid amount: {amount_str}")
```

#### 2. Date Validation
```python
def validate_date(date_str):
    formats = [
        '%Y-%m-%d',      # ISO format
        '%m/%d/%Y',      # US format
        '%d/%m/%Y',      # EU format
        '%Y/%m/%d',      # Alternative
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    raise ValidationError(f"Invalid date format: {date_str}")
```

#### 3. Enum Validation
```python
MOVEMENT_TYPES = {'INCOME', 'EXPENSE', 'TRANSFER'}
ACCOUNT_TYPES = {'SAVINGS', 'CREDIT', 'CASH', 'INVESTMENT', 'OTHER'}
BILLING_CYCLES = {'weekly', 'monthly', 'quarterly', 'yearly'}

def validate_enum(value, valid_values, field_name):
    if value not in valid_values:
        raise ValidationError(
            f"Invalid {field_name}: {value}. "
            f"Must be one of: {', '.join(valid_values)}"
        )
    return value
```

### Business Rule Validations

#### 1. Account Type Consistency
```python
def validate_account_transaction(row):
    if row.get('credit_card_name') and row.get('account_type') != 'CREDIT':
        raise ValidationError(
            "Credit card transaction must have CREDIT account type"
        )
```

#### 2. Transfer Validation
```python
def validate_transfer(row):
    if row.get('transaction_movement_type') == 'TRANSFER':
        if not (row.get('from_account_name') and row.get('to_account_name')):
            raise ValidationError(
                "Transfer must have both from and to accounts"
            )
        if row.get('from_account_name') == row.get('to_account_name'):
            raise ValidationError(
                "Transfer cannot be between same account"
            )
```

## Performance Optimization

### Export Optimizations

#### 1. Batch Fetching
```python
# Instead of N+1 queries
transactions = session.query(Transaction).filter(
    Transaction.user_id == user_id
).options(
    joinedload(Transaction.account),
    joinedload(Transaction.credit_card),
    joinedload(Transaction.category),
    joinedload(Transaction.vendor)
).all()
```

#### 2. Streaming Large Exports
```python
def stream_csv_export(user_id):
    def generate():
        # Write headers
        yield ','.join(CSV_HEADERS) + '\n'

        # Stream transactions in chunks
        offset = 0
        chunk_size = 1000

        while True:
            transactions = fetch_transactions(
                user_id,
                offset=offset,
                limit=chunk_size
            )

            if not transactions:
                break

            for transaction in transactions:
                row = transaction_to_csv_row(transaction)
                yield ','.join(row.values()) + '\n'

            offset += chunk_size

    return StreamingResponse(generate(), media_type='text/csv')
```

### Import Optimizations

#### 1. Bulk Insert
```python
# Instead of individual inserts
session.bulk_insert_mappings(Transaction, transaction_dicts)
session.commit()
```

#### 2. Caching Lookups
```python
class EntityCache:
    def __init__(self):
        self.cache = {}

    def get_or_fetch(self, key, fetch_func):
        if key not in self.cache:
            self.cache[key] = fetch_func(key)
        return self.cache[key]

# Use cache during import
cache = EntityCache()
for row in csv_rows:
    account_id = cache.get_or_fetch(
        row['account_name'],
        lambda name: find_account_by_name(name, user_id)
    )
```

## Security Measures

### Input Sanitization
```python
def sanitize_csv_field(value):
    # Prevent CSV injection
    if value and value[0] in ['=', '+', '-', '@']:
        value = "'" + value

    # Remove null bytes
    value = value.replace('\0', '')

    # Truncate excessive length
    max_length = 1000
    if len(value) > max_length:
        value = value[:max_length]

    return value
```

### File Upload Security
```python
def validate_upload(file):
    # Check file size
    max_size = 50 * 1024 * 1024  # 50MB
    if file.size > max_size:
        raise ValidationError("File too large")

    # Check MIME type
    allowed_types = ['text/csv', 'application/csv']
    if file.content_type not in allowed_types:
        raise ValidationError("Invalid file type")

    # Check file extension
    if not file.filename.lower().endswith('.csv'):
        raise ValidationError("File must be CSV")

    # Scan first few bytes for magic numbers
    header = file.read(1024)
    file.seek(0)  # Reset position

    if b'<script' in header or b'<?php' in header:
        raise ValidationError("File contains suspicious content")
```

## Testing Scenarios

### Edge Cases to Test

1. **Empty Data**
   - User with no transactions
   - Transactions with no categories
   - Accounts with no transactions

2. **Maximum Limits**
   - 100,000 transactions
   - 1,000 character descriptions
   - Maximum decimal values

3. **Special Characters**
   - Commas in descriptions
   - Quotes in names
   - Unicode characters
   - Line breaks in text

4. **Data Integrity**
   - Circular category references
   - Orphaned transactions
   - Duplicate names
   - Case sensitivity

5. **Concurrent Operations**
   - Multiple imports simultaneously
   - Export during import
   - Database locks

## Monitoring and Logging

### Key Metrics
```python
# Track import/export metrics
metrics = {
    'export_duration': time.time() - start_time,
    'row_count': len(transactions),
    'file_size': len(csv_content),
    'memory_usage': psutil.Process().memory_info().rss
}

logger.info(f"Export completed: {metrics}")
```

### Audit Trail
```python
# Log all import operations
audit_log = {
    'user_id': user_id,
    'operation': 'import',
    'timestamp': datetime.utcnow(),
    'file_name': file.filename,
    'file_size': file.size,
    'rows_processed': row_count,
    'entities_created': created_counts,
    'errors': error_list,
    'duration': duration
}

save_audit_log(audit_log)
```

## Troubleshooting Guide

### Common Problems and Solutions

| Problem | Possible Cause | Solution |
|---------|---------------|----------|
| Import creates duplicates | Name changes between export/import | Use stricter duplicate detection |
| Categories not hierarchical | Import order issue | Process parents before children |
| Transactions missing accounts | Account creation failed | Check broker exists first |
| Large file timeout | Synchronous processing | Implement async/background jobs |
| Memory error on export | Loading all data at once | Use streaming/chunking |
| Character encoding errors | Non-UTF8 CSV | Detect and convert encoding |

## Future Improvements

1. **Incremental Sync**
   - Track last export/import timestamp
   - Only process changes since last sync

2. **Conflict Resolution**
   - User interface for resolving duplicates
   - Merge strategies for similar records

3. **Data Transformation**
   - Currency conversion during import
   - Date format auto-detection
   - Category mapping rules

4. **Advanced Features**
   - Scheduled exports to cloud storage
   - Email notifications on completion
   - Progress websocket updates
   - Compression for large exports