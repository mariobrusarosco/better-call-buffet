# Category Migration Strategy

**Feature:** Migrating from String Categories to User-Defined Category System
**Risk Level:** Medium (production data modification)
**Rollback:** Yes (keep old `category` column during migration)
**Estimated Time:** 30-60 minutes (depending on data volume)

---

## Overview

This guide walks through safely migrating existing transaction categories from simple strings to the new user-defined category system with hierarchy.

**What Changes:**
- `transactions.category` (String) → `transactions.category_id` (UUID FK)
- Create `user_categories` table with user-specific categories
- Extract unique category strings and convert to `UserCategory` records

**Migration Approach:**
- ✅ Non-destructive (keeps old column as backup)
- ✅ Reversible (can rollback)
- ✅ Testable (run on copy of production DB first)
- ✅ Preserves all transaction data

---

## Prerequisites

Before starting migration:

**1. Backup Database**
```bash
# Create full database backup
pg_dump $DATABASE_URL > backup_before_category_migration_$(date +%Y%m%d).sql
```

**2. Test Environment**
- Create copy of production database
- Run full migration on test copy first
- Verify data integrity

**3. Deployment Window**
- Plan maintenance window (30-60 min)
- Notify users of potential downtime
- Prepare rollback plan

---

## Phase 1: Add New Structure (Non-Breaking)

**Goal:** Add new tables/columns without breaking existing functionality.

### Step 1.1: Create Migration

**File:** `migrations/versions/xxx_add_user_categories_table.py`

```python
"""Add user_categories table and category_id to transactions

Revision ID: xxx
Revises: previous_revision
Create Date: 2024-12-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'xxx'
down_revision = 'previous_revision'
branch_labels = None
depends_on = None


def upgrade():
    # Create user_categories table
    op.create_table(
        'user_categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),

        # Foreign keys
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_id'], ['user_categories.id'], ondelete='CASCADE'),

        # Constraints
        sa.UniqueConstraint('user_id', 'name', 'parent_id', name='uq_user_category_name'),
    )

    # Create indexes
    op.create_index('idx_user_categories_user_parent', 'user_categories', ['user_id', 'parent_id'])
    op.create_index('idx_user_categories_user_active', 'user_categories', ['user_id', 'is_active'])

    # Add category_id to transactions (nullable for now)
    op.add_column(
        'transactions',
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=True)
    )

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_transactions_category_id',
        'transactions',
        'user_categories',
        ['category_id'],
        ['id']
    )

    # Create index for fast lookups
    op.create_index('idx_transactions_category', 'transactions', ['category_id'])

    # NOTE: Keep old 'category' column for now (rollback safety)


def downgrade():
    # Drop indexes
    op.drop_index('idx_transactions_category', 'transactions')
    op.drop_index('idx_user_categories_user_active', 'user_categories')
    op.drop_index('idx_user_categories_user_parent', 'user_categories')

    # Drop foreign key and column
    op.drop_constraint('fk_transactions_category_id', 'transactions', type_='foreignkey')
    op.drop_column('transactions', 'category_id')

    # Drop user_categories table
    op.drop_table('user_categories')
```

### Step 1.2: Run Migration

```bash
# Apply migration
docker compose exec web alembic upgrade head

# Verify tables created
docker compose exec web python -c "
from app.db.connection_and_session import engine
from sqlalchemy import inspect
inspector = inspect(engine)
print('user_categories table exists:', 'user_categories' in inspector.get_table_names())
"
```

---

## Phase 2: Data Migration Script

**Goal:** Convert existing string categories to UserCategory records and link transactions.

### Step 2.1: Analysis Script

**File:** `scripts/analyze_categories.py`

```python
"""
Analyze existing category data before migration.

Run this to understand what you're migrating:
- How many unique categories per user?
- Which categories are most common?
- Any empty/null categories?
"""
import sys
import os
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings


def analyze_categories():
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # Get unique categories per user
        result = db.execute(text("""
            SELECT
                user_id,
                category,
                COUNT(*) as transaction_count
            FROM transactions
            WHERE category IS NOT NULL
              AND category != ''
              AND is_deleted = FALSE
            GROUP BY user_id, category
            ORDER BY user_id, transaction_count DESC
        """))

        user_categories = defaultdict(list)
        total_transactions = 0

        for row in result:
            user_id = str(row.user_id)
            category = row.category
            count = row.transaction_count

            user_categories[user_id].append({
                'category': category,
                'count': count
            })
            total_transactions += count

        print("=" * 60)
        print("CATEGORY MIGRATION ANALYSIS")
        print("=" * 60)
        print(f"\nTotal users with categories: {len(user_categories)}")
        print(f"Total transactions to migrate: {total_transactions}\n")

        for user_id, categories in user_categories.items():
            print(f"\nUser: {user_id}")
            print(f"  Unique categories: {len(categories)}")
            print(f"  Categories:")
            for cat in categories[:10]:  # Show top 10
                print(f"    - '{cat['category']}': {cat['count']} transactions")
            if len(categories) > 10:
                print(f"    ... and {len(categories) - 10} more")

        # Check for empty categories
        empty_result = db.execute(text("""
            SELECT COUNT(*) as count
            FROM transactions
            WHERE (category IS NULL OR category = '')
              AND is_deleted = FALSE
        """))
        empty_count = empty_result.first().count

        if empty_count > 0:
            print(f"\n⚠️  WARNING: {empty_count} transactions have empty/null categories")
            print("   These will be skipped during migration")

    except Exception as e:
        print(f"Error analyzing categories: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    analyze_categories()
```

**Run Analysis:**
```bash
docker compose exec web python scripts/analyze_categories.py
```

### Step 2.2: Migration Script

**File:** `scripts/migrate_categories.py`

```python
"""
Migrate existing string categories to user-defined category system.

This script:
1. Extracts unique category strings per user
2. Creates UserCategory records (top-level only)
3. Updates transactions.category_id to reference new categories
4. Keeps old category column as backup
"""
import sys
import os
import uuid
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.domains.categories.models import UserCategory


def migrate_categories(dry_run=True):
    """
    Migrate categories from strings to user_categories table.

    Args:
        dry_run: If True, only print what would be done (don't commit)
    """
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        print("=" * 60)
        print("CATEGORY MIGRATION" + (" (DRY RUN)" if dry_run else " (LIVE)"))
        print("=" * 60)

        # Step 1: Get all users with transactions
        users_result = db.execute(text("""
            SELECT DISTINCT user_id
            FROM transactions
            WHERE category IS NOT NULL
              AND category != ''
              AND is_deleted = FALSE
        """))

        user_ids = [row.user_id for row in users_result]
        print(f"\n📊 Found {len(user_ids)} users with categorized transactions\n")

        total_categories_created = 0
        total_transactions_updated = 0

        # Step 2: Process each user
        for user_id in user_ids:
            print(f"\n👤 Processing user: {user_id}")

            # Get unique categories for this user
            categories_result = db.execute(text("""
                SELECT DISTINCT category, COUNT(*) as count
                FROM transactions
                WHERE user_id = :user_id
                  AND category IS NOT NULL
                  AND category != ''
                  AND is_deleted = FALSE
                GROUP BY category
                ORDER BY count DESC
            """), {"user_id": user_id})

            categories = list(categories_result)
            print(f"   Found {len(categories)} unique categories")

            # Mapping: old_string → new_uuid
            category_mapping = {}

            # Step 3: Create UserCategory records
            for i, row in enumerate(categories, start=1):
                category_name = row.category.strip()
                transaction_count = row.count

                # Create UserCategory
                new_category = UserCategory(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    name=category_name,
                    parent_id=None,  # Top-level
                    display_order=i,
                    is_active=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )

                if not dry_run:
                    db.add(new_category)
                    db.flush()  # Get ID without committing yet

                category_mapping[category_name] = new_category.id

                print(f"   ✓ Created category '{category_name}' → {new_category.id} ({transaction_count} txns)")
                total_categories_created += 1

            # Step 4: Update transactions
            if not dry_run:
                for old_name, new_id in category_mapping.items():
                    result = db.execute(text("""
                        UPDATE transactions
                        SET category_id = :category_id
                        WHERE user_id = :user_id
                          AND category = :old_category
                          AND is_deleted = FALSE
                    """), {
                        "category_id": new_id,
                        "user_id": user_id,
                        "old_category": old_name
                    })
                    total_transactions_updated += result.rowcount

        # Step 5: Verify migration
        print(f"\n{'=' * 60}")
        print("MIGRATION SUMMARY")
        print(f"{'=' * 60}")
        print(f"Users processed: {len(user_ids)}")
        print(f"Categories created: {total_categories_created}")
        print(f"Transactions updated: {total_transactions_updated}")

        if not dry_run:
            # Verification query
            orphaned = db.execute(text("""
                SELECT COUNT(*) as count
                FROM transactions
                WHERE category IS NOT NULL
                  AND category != ''
                  AND category_id IS NULL
                  AND is_deleted = FALSE
            """)).first().count

            if orphaned > 0:
                print(f"\n⚠️  WARNING: {orphaned} transactions still have null category_id!")
                print("   Rolling back migration...")
                db.rollback()
                return False
            else:
                print(f"\n✅ Verification passed: All categorized transactions have category_id")
                db.commit()
                print("✅ Migration committed successfully!")
                return True
        else:
            print(f"\n🔍 DRY RUN - No changes made to database")
            print("   Run with --live to apply changes")
            db.rollback()
            return True

    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate categories to user-defined system")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Actually perform migration (default is dry-run)"
    )

    args = parser.parse_args()

    success = migrate_categories(dry_run=not args.live)
    sys.exit(0 if success else 1)
```

### Step 2.3: Run Migration

**Test First (Dry Run):**
```bash
# See what would happen (no changes)
docker compose exec web python scripts/migrate_categories.py

# Review output carefully
```

**Run Live Migration:**
```bash
# Backup database first!
docker compose exec db pg_dump -U postgres better_call_buffet > backup_$(date +%Y%m%d_%H%M%S).sql

# Run migration for real
docker compose exec web python scripts/migrate_categories.py --live
```

**Expected Output:**
```
============================================================
CATEGORY MIGRATION (LIVE)
============================================================

📊 Found 3 users with categorized transactions

👤 Processing user: 550e8400-e29b-41d4-a716-446655440000
   Found 8 unique categories
   ✓ Created category 'Rent' → uuid-1 (42 txns)
   ✓ Created category 'Food' → uuid-2 (35 txns)
   ...

============================================================
MIGRATION SUMMARY
============================================================
Users processed: 3
Categories created: 24
Transactions updated: 156

✅ Verification passed: All categorized transactions have category_id
✅ Migration committed successfully!
```

---

## Phase 3: Seed Default Categories for New Users

**Goal:** New users get pre-populated categories automatically.

### Step 3.1: Update User Registration

**File:** `app/domains/users/service.py` (or wherever user creation happens)

```python
from app.db.seeds.default_categories import seed_default_categories

class UserService:
    def create_user(self, user_data: UserCreate) -> User:
        # ... existing user creation logic ...

        new_user = User(**user_dict)
        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)

        # NEW: Seed default categories for new user
        try:
            seed_default_categories(self.db, new_user.id)
            logger.info(f"Seeded default categories for user {new_user.id}")
        except Exception as e:
            logger.error(f"Failed to seed categories for user {new_user.id}: {e}")
            # Don't fail user creation if category seeding fails

        return new_user
```

---

## Phase 4: Update Transaction Domain

**Goal:** Transactions now use `category_id` instead of `category` string.

### Step 4.1: Update Schemas

**File:** `app/domains/transactions/schemas.py`

```python
# BEFORE (deprecated):
class TransactionIn(TransactionBase):
    category: str  # ← Remove this

# AFTER (new):
class TransactionIn(TransactionBase):
    category_id: UUID  # ← Add this
```

### Step 4.2: Update Service Validation

**File:** `app/domains/transactions/service.py`

```python
from app.domains.categories.repository import CategoryRepository

class TransactionService:
    def create_transaction(self, transaction: TransactionIn, user_id: UUID) -> Transaction:
        # NEW: Validate category exists and belongs to user
        category_repo = CategoryRepository(self.db)
        category = category_repo.get_by_id(transaction.category_id, user_id)

        if not category:
            raise HTTPException(
                status_code=404,
                detail="Category not found"
            )

        # ... rest of transaction creation ...
```

### Step 4.3: Update Filters

**File:** `app/domains/transactions/repository.py`

```python
# BEFORE:
if filters.category:
    query = query.filter(Transaction.category.ilike(f"%{filters.category}%"))

# AFTER:
if filters.category_id:
    query = query.filter(Transaction.category_id == filters.category_id)
```

---

## Phase 5: Cleanup (After Frontend Updates)

**Goal:** Remove old `category` column and enforce new structure.

### Step 5.1: Final Migration

**File:** `migrations/versions/xxx_cleanup_category_migration.py`

```python
"""Remove old category column and make category_id required

Revision ID: xxx
Revises: previous_revision
Create Date: 2024-12-21
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    # Make category_id NOT NULL (enforce going forward)
    op.alter_column(
        'transactions',
        'category_id',
        nullable=False
    )

    # Drop old category column
    op.drop_column('transactions', 'category')


def downgrade():
    # Re-add category column
    op.add_column(
        'transactions',
        sa.Column('category', sa.String(), nullable=True)
    )

    # Make category_id nullable again
    op.alter_column(
        'transactions',
        'category_id',
        nullable=True
    )
```

### Step 5.2: Run Cleanup

```bash
# Only run after:
# 1. Data migration is complete
# 2. Frontend is updated to use category_id
# 3. No rollback needed

docker compose exec web alembic upgrade head
```

---

## Rollback Plan

If something goes wrong, you can rollback:

### Option 1: Rollback Immediately (Before Cleanup Phase)

```bash
# Restore from backup
docker compose exec db psql -U postgres better_call_buffet < backup_before_migration.sql

# Or manually rollback:
docker compose exec web alembic downgrade -1
```

### Option 2: Restore Old Functionality

```python
# In transactions/service.py, temporarily support both:

if hasattr(transaction, 'category_id') and transaction.category_id:
    # Use new system
    validate_category_id(transaction.category_id, user_id)
elif hasattr(transaction, 'category') and transaction.category:
    # Use old system (backward compatibility)
    # No validation needed
else:
    # Neither provided
    raise HTTPException(400, "Category required")
```

---

## Verification Checklist

After migration, verify:

**Database Checks:**
```sql
-- 1. All categorized transactions have category_id
SELECT COUNT(*) FROM transactions
WHERE category IS NOT NULL
  AND category != ''
  AND category_id IS NULL;
-- Expected: 0

-- 2. All category_ids reference valid categories
SELECT COUNT(*) FROM transactions t
LEFT JOIN user_categories uc ON t.category_id = uc.id
WHERE t.category_id IS NOT NULL
  AND uc.id IS NULL;
-- Expected: 0

-- 3. User categories look reasonable
SELECT user_id, COUNT(*) as category_count
FROM user_categories
WHERE is_active = TRUE
GROUP BY user_id;
-- Expected: Reasonable counts per user
```

**API Checks:**
```bash
# 1. Get categories endpoint works
curl -X GET http://localhost:8000/api/v1/categories \
  -H "Authorization: Bearer <token>"

# 2. Create transaction with category_id works
curl -X POST http://localhost:8000/api/v1/transactions \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "category_id": "<valid-category-uuid>",
    "amount": 100,
    ...
  }'
```

---

## Timeline & Coordination

**Recommended Deployment Sequence:**

**Day 1 (Backend - Non-Breaking):**
1. Deploy Phase 1 migration (add tables/columns)
2. Run data migration script
3. Seed default categories for existing users (optional)
4. Test thoroughly on production

**Day 2-7 (Frontend Update):**
5. Frontend team updates to use new category endpoints
6. Frontend shows cascading dropdowns
7. Thorough testing

**Day 8 (Cleanup):**
8. Deploy Phase 5 cleanup (remove old column)
9. Monitor for issues

---

## Monitoring & Alerts

**Watch for:**
- Failed category validations (404 errors)
- Slow category tree queries
- Orphaned transactions (category_id NULL)

**Log Key Metrics:**
```python
logger.info(
    "Category migration metrics",
    extra={
        "categories_created": total_categories_created,
        "transactions_updated": total_transactions_updated,
        "duration_seconds": duration,
    }
)
```

---

## FAQs

**Q: What if users have typos like "Food" vs "food"?**
A: They'll create separate categories. Users can manually merge by:
1. Update transactions to use correct category
2. Delete the typo category

**Q: Can we auto-detect sub-categories from strings like "Rent - Family"?**
A: Possible but complex. Current script creates only top-level categories. Users can manually organize into sub-categories after migration.

**Q: What if a user deletes a category that has transactions?**
A: The API prevents this (soft delete only). Transactions keep their category_id.

**Q: How long will migration take?**
A: Depends on data volume:
- 1,000 transactions: ~30 seconds
- 10,000 transactions: ~2 minutes
- 100,000 transactions: ~10 minutes

---

## Summary

**Migration Steps:**
1. ✅ Phase 1: Add new structure (non-breaking)
2. ✅ Phase 2: Run data migration script
3. ✅ Phase 3: Seed defaults for new users
4. ✅ Phase 4: Update transaction domain
5. ✅ Phase 5: Cleanup old column (breaking)

**Safety Measures:**
- ✅ Dry-run mode
- ✅ Database backup
- ✅ Old column kept during migration
- ✅ Verification queries
- ✅ Rollback plan

**Next Steps:**
See `docs/domains/user-categories.md` for implementation guide.
