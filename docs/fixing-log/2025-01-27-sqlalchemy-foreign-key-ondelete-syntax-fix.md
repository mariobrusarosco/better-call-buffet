# SQLAlchemy Foreign Key ON DELETE CASCADE Syntax Fix

## Issue Context

**Date:** 2025-01-27  
**Error:** `TypeError: Additional arguments should be named <dialectname>_<argument>, got 'ondelete'`  
**Command:** `docker compose exec web alembic revision --autogenerate -m "Refactor balance_points domain with timeline tracking"`

## Problem Description

The error occurred when trying to generate an Alembic migration for the `BalancePoint` model. The issue was in the foreign key definition where `ondelete="CASCADE"` was used directly as an argument to the `ForeignKey` constructor.

**Problematic Code:**

```python
account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), ondelete="CASCADE", nullable=False)
```

## Root Cause

In SQLAlchemy, foreign key constraints with `ON DELETE CASCADE` cannot be defined directly as arguments to the `ForeignKey` constructor. The `ondelete` parameter is not a valid argument for `ForeignKey` - it needs to be defined using the `ForeignKeyConstraint` class.

## Solution Applied

1. **Added ForeignKeyConstraint import:**

   ```python
   from sqlalchemy import (
       # ... other imports
       ForeignKeyConstraint,
       # ... other imports
   )
   ```

2. **Removed ondelete from ForeignKey:**

   ```python
   # Before
   account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), ondelete="CASCADE", nullable=False)

   # After
   account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
   ```

3. **Added ForeignKeyConstraint to **table_args**:**
   ```python
   __table_args__ = (
       ForeignKeyConstraint(
           ["account_id"],
           ["accounts.id"],
           ondelete="CASCADE",
           name="fk_balance_points_account_id"
       ),
       # ... other constraints
   )
   ```

## Key Learning Points

- **SQLAlchemy Foreign Key Constraints:** Use `ForeignKeyConstraint` class for defining `ON DELETE CASCADE` behavior
- **Table-level Constraints:** Foreign key constraints with additional options should be defined in `__table_args__`
- **Naming Conventions:** Always provide explicit names for constraints for better database management

## Files Modified

- `app/domains/balance_points/models.py`

## Verification

The fix resolves the SQLAlchemy syntax error and allows Alembic to properly generate migrations for the balance points domain refactoring.

## Related Concepts

- SQLAlchemy Foreign Key Constraints
- Database Migration Best Practices
- Alembic Auto-generation
- PostgreSQL Foreign Key Behavior
