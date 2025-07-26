# Decision Record: Database Seeding Strategy (DR-006)

## Status

Accepted (June 8, 2025)

## Context

The Better Call Buffet application requires a consistent and reliable way to populate the database with initial data for both development and production environments. We needed to determine:

1. How to structure the seeding process
2. What data should be seeded
3. How to handle different environments (dev vs prod)
4. How to maintain data consistency with foreign key relationships

## Decision

We have decided to implement a centralized seeding script (`scripts/seed_db.py`) with the following key features:

### Core Features

1. **Truncation with Foreign Key Handling**:

   ```python
   def truncate_tables(db):
       db.execute(text("SET session_replication_role = 'replica';"))
       for table in ["accounts", "brokers", "users"]:
           db.execute(text(f"TRUNCATE TABLE {table} CASCADE;"))
       db.execute(text("SET session_replication_role = 'origin';"))
   ```

2. **Fixed Test User ID**:

   ```python
   test_user = User(
       email="test@example.com",
       name="Test User",
       id=get_current_user_id()  # Fixed UUID for consistency
   )
   ```

3. **Environment-Aware Configuration**:
   ```python
   DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/better_call_buffet"
   ```

### Seeding Order

1. Users (base entities)
2. Brokers (with user relationships)
3. Accounts (with user relationships)

## Alternatives Considered

### 1. Separate Seeds per Domain

- **Pros**: More modular, domain-specific control
- **Cons**: Complex dependency management, harder to maintain order
- **Why Rejected**: Centralized approach provides better control over seeding order

### 2. SQL-Based Seeding

- **Pros**: Database-native approach, potentially faster
- **Cons**: Less flexible, harder to maintain relationships
- **Why Rejected**: Python approach provides better integration with our models

### 3. Factory-Based Seeding

- **Pros**: More flexible for testing
- **Cons**: Overkill for our current needs
- **Why Rejected**: Simple script approach sufficient for current requirements

## Consequences

### Positive

1. Single source of truth for seeding
2. Consistent test data across environments
3. Automatic handling of foreign key relationships
4. Easy to run from command line or CI/CD
5. Transaction-based for data consistency

### Negative

1. Need to maintain seeding order manually
2. Single script could grow large over time
3. Same seed data in all environments

### Mitigations

1. Clear comments and structure in seed script
2. Environment-specific configuration options
3. Regular review and cleanup of seed data

## Implementation Notes

### Running the Seeder

```bash
# Local development
poetry run python scripts/seed_db.py

# Production (if needed)
python scripts/seed_db.py
```

### Adding New Seeds

1. Add new models to truncation list
2. Create entities in correct order
3. Add appropriate relationships
4. Test locally before committing

## Related Documents

- Database Migrations: See CLAUDE.md for migration commands

## Notes

This decision should be revisited when:

- Adding new domains with complex relationships
- Implementing different environment needs
- Performance issues arise with larger datasets
- Testing requirements change
