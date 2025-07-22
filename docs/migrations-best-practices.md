# Migration Best Practices for FastAPI + SQLAlchemy

## Professional Patterns for Model Discovery

### 1. **Centralized Registration** (Current Implementation)
✅ **What we implemented**: Single `model_registration.py` file imports all models

**Pros:**
- Simple and explicit
- Easy to understand and debug
- Clear control over what gets registered

**Cons:**
- Still requires manual updates when adding domains
- Can forget to add new models

**Usage:**
```python
# app/db/model_registration.py
from app.domains.new_domain.models import NewModel  # Add this line for new domains
```

### 2. **Auto-Discovery Pattern** (Advanced)
🚀 **For larger projects**: Automatically find all model files

```python
# app/db/auto_model_discovery.py
import importlib
import pkgutil
from pathlib import Path

def auto_import_models():
    """Automatically import all models.py files from domains"""
    domains_path = Path(__file__).parent.parent / "domains"
    
    for domain_dir in domains_path.iterdir():
        if domain_dir.is_dir() and not domain_dir.name.startswith('_'):
            models_file = domain_dir / "models.py"
            if models_file.exists():
                module_name = f"app.domains.{domain_dir.name}.models"
                try:
                    importlib.import_module(module_name)
                    print(f"✅ Auto-imported models from {module_name}")
                except ImportError as e:
                    print(f"❌ Failed to import {module_name}: {e}")

# Call this in model_registration.py
auto_import_models()
```

### 3. **Plugin Pattern** (Enterprise)
🏢 **For very large projects**: Registry-based approach

```python
# app/db/model_registry.py
class ModelRegistry:
    _models = set()
    
    @classmethod
    def register(cls, model_class):
        cls._models.add(model_class)
        return model_class
    
    @classmethod
    def get_all_models(cls):
        return cls._models

# Usage in models:
from app.db.model_registry import ModelRegistry

@ModelRegistry.register
class Account(Base):
    __tablename__ = "accounts"
    # ...
```

## Migration Workflow Best Practices

### 1. **Development Workflow**
```bash
# 1. Create/modify models
# 2. Generate migration
docker exec better-call-buffet-web-1 poetry run alembic revision --autogenerate -m "descriptive message"

# 3. Review generated migration
cat migrations/versions/latest_migration.py

# 4. Apply migration
docker exec better-call-buffet-web-1 poetry run alembic upgrade head

# 5. Verify in database
docker exec better-call-buffet-db-1 psql -U postgres -d better_call_buffet -c "\d table_name"
```

### 2. **Migration Naming Conventions**
- `add_user_profile_table` - New table
- `make_email_nullable_in_users` - Column change
- `add_index_to_user_email` - Index creation
- `remove_deprecated_status_column` - Column removal

### 3. **Migration Review Checklist**
- [ ] Migration creates expected tables/columns
- [ ] Foreign keys are correct
- [ ] Indexes are appropriate
- [ ] Downgrade function works
- [ ] No data loss in production migration

### 4. **Production Migration Strategy**
```bash
# 1. Backup database
pg_dump better_call_buffet > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Test migration on staging
alembic upgrade head

# 3. Monitor application after migration
# 4. Have rollback plan ready
```

## Common Migration Issues

### 1. **Model Not Found**
❌ Problem: `Table 'new_table' doesn't exist`
✅ Solution: Ensure model is imported in `model_registration.py`

### 2. **Empty Migration Generated**
❌ Problem: Migration has only `pass` statements
✅ Solution: Check model imports and Base inheritance

### 3. **Foreign Key Errors**
❌ Problem: `Foreign key constraint fails`
✅ Solution: Ensure referenced table exists, check column types

### 4. **Migration Conflicts**
❌ Problem: Multiple developers create migrations with same parent
✅ Solution: Use `alembic merge` to create merge migration

## Alternative Tools

### 1. **Alembic Alternatives**
- **SQLModel** (Pydantic + SQLAlchemy): Simpler for small projects
- **Aerich** (Tortoise ORM): Async-first ORM
- **Yoyo Migrations**: Lightweight alternative

### 2. **Database-First Approaches**
- **SQLAlchemy Automap**: Generate models from existing database
- **DB-First Tools**: Use database schema as source of truth

## FastAPI-Specific Tips

### 1. **Startup Events**
```python
# app/main.py
@app.on_event("startup")
async def startup_event():
    # Validate all models are registered
    from app.db.model_registration import validate_model_registration
    validate_model_registration()
```

### 2. **Health Check Integration**
```python
# Include migration status in health checks
@router.get("/health/migrations")
def migration_health():
    from alembic import command
    from alembic.config import Config
    
    # Check if migrations are up to date
    # Return status
```

## Recommended Approach

For your project size, **stick with the Centralized Registration pattern** we implemented:

1. ✅ Simple and reliable
2. ✅ Easy to understand for team members
3. ✅ Good balance of automation and control
4. ✅ Industry standard for medium-sized projects

When you add a new domain:
1. Create the models
2. Add import to `app/db/model_registration.py`
3. Generate migration
4. Review and apply

This prevents the import issues while keeping complexity manageable!