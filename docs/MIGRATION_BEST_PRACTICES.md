# Migration Best Practices - Never Break Again

This document establishes bulletproof migration practices to prevent the chaos we just resolved.

## 🚨 The Problem We Fixed

- **Model-Migration Drift**: SQLAlchemy models evolved but migrations didn't keep up
- **Circular Dependencies**: Complex foreign key relationships causing table creation order issues  
- **Autogenerate Chaos**: One massive migration trying to fix everything at once
- **8 Reset Cycles**: Unacceptable professional standard

## ✅ The Solution: Clean Slate + Strict Workflow

### Step 1: Clean Baseline (DONE)
- ✅ Nuclear reset: `docker-compose down -v`
- ✅ Clean migration history: Deleted all migration files
- ✅ Single initial migration: `001_initial_schema.py` with proper table order
- ✅ Working seed script: Direct SQL inserts to avoid SQLAlchemy validation issues

### Step 2: Ironclad Rules Going Forward

#### Rule 1: NEVER Use Autogenerate on Existing Projects
```bash
# ❌ NEVER DO THIS (causes chaos)
alembic revision --autogenerate -m "Some change"

# ✅ ALWAYS DO THIS (controlled)
alembic revision -m "Add specific_field to specific_table"
# Then manually write the migration
```

#### Rule 2: One Change Per Migration
```python
# ✅ GOOD - Single, specific change
def upgrade():
    op.add_column('users', sa.Column('phone', sa.String(), nullable=True))

# ❌ BAD - Multiple unrelated changes
def upgrade():
    op.add_column('users', sa.Column('phone', sa.String(), nullable=True))
    op.alter_column('accounts', 'balance', type_=sa.DECIMAL(15,2))
    op.create_table('new_feature', ...)
```

#### Rule 3: Test Migrations Locally FIRST
```bash
# ✅ REQUIRED workflow
1. alembic revision -m "Add phone to users"
2. Edit migration file manually
3. alembic upgrade head  # Test locally
4. Test rollback: alembic downgrade -1
5. alembic upgrade head  # Re-apply
6. Run seed script to verify
7. Only then commit and push
```

#### Rule 4: Never Skip Migration Testing
```bash
# ✅ ALWAYS test both directions
docker-compose exec web alembic upgrade head
docker-compose exec web alembic downgrade -1  
docker-compose exec web alembic upgrade head
docker-compose exec web python scripts/seed_db.py
```

#### Rule 5: Handle Foreign Keys Carefully
```python
# ✅ GOOD - Create tables in dependency order
def upgrade():
    # 1. Create parent tables first
    op.create_table('users', ...)
    op.create_table('brokers', ...)
    
    # 2. Create child tables without circular FKs  
    op.create_table('accounts', ...)
    
    # 3. Add circular FK constraints last
    op.create_foreign_key('fk_name', 'table', 'target', ['col'], ['id'])
```

## 🔧 Emergency Procedures

### If Migration Fails in CI
```bash
# 1. Don't panic, don't force push
# 2. Fix locally first
docker-compose down -v  # Reset local DB
docker-compose up -d
alembic upgrade head    # Test the fix

# 3. Only then push the fix
```

### If You Need to Modify Models
```bash
# 1. Don't use autogenerate
# 2. Create manual migration
alembic revision -m "Add specific_field_to_table"

# 3. Edit the migration file manually
# 4. Test locally
# 5. Test rollback  
# 6. Commit only after testing
```

## 📋 Migration Checklist

Before ANY migration gets committed:

- [ ] Migration has a descriptive name
- [ ] Migration does ONE specific thing
- [ ] Tested `alembic upgrade head` locally
- [ ] Tested `alembic downgrade -1` (rollback)
- [ ] Tested `alembic upgrade head` again
- [ ] Seed script still works
- [ ] API endpoints still work
- [ ] CI will pass (no foreign key issues)

## 🎯 Current State (Clean Baseline)

**Migration:** `001_initial_schema` 
**Database:** Clean, seeded with test data
**API:** Working with proper relationships
**Models:** In sync with database schema

**Next Changes Must Follow These Rules!**

## 🚫 Never Again

We will NEVER again:
- Use autogenerate on this project
- Create massive migrations
- Skip local testing
- Reset the database 9 times
- Have unprofessional migration chaos

The foundation is now solid. Build on it responsibly.