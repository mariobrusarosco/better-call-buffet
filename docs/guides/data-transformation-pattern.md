# 🎓 Data Transformation Pattern Guide

## The 3-Layer Rule

```
Router Layer    →  Pydantic Schema  →  .model_dump()  →  Dict
Service Layer   →  Dict             →  (validation)   →  Dict
Repository Layer→  Dict             →  ORM(**dict)    →  Database
```

| Layer      | Input Type      | Output Type     |
| ---------- | --------------- | --------------- |
| Router     | Pydantic Schema | Pydantic Schema |
| Service    | Dict            | ORM Model       |
| Repository | Dict or ORM     | ORM Model       |

🎯 The Pattern You Should Always Follow

# ROUTER

```
  @router.post("", response_model=Category)  # ← Pydantic
  def create(input: CategoryCreate):  # ← Pydantic
      data = input.model_dump()  # ← Convert to dict
      orm = service.create(data)  # ← Service returns ORM
      return Category.from_orm(orm)  # ← Convert ORM to Pydantic
```

# SERVICE

```
  def create(self, data: dict) -> UserCategory:  # ← Dict in, ORM out
      # Validate dict
      return self.repository.create(data)  # ← Pass dict to repo
```

# REPOSITORY

```
  def create(self, data: dict) -> UserCategory:  # ← Dict in, ORM out
      obj = UserCategory(**data)  # ← Convert dict to ORM
      self.db.add(obj)
      self.db.commit()
      return obj  # ← Return ORM
```

---

## 📋 Layer-by-Layer Pattern

### 1. Router Layer (Receives & Returns Schemas)

**Responsibilities:**

- Receive Pydantic schemas from HTTP requests
- Convert schemas to dicts for service layer
- Convert ORM responses back to schemas
- Add `response_model` for validation

**Pattern:**

```python
@router.post("", response_model=Category, status_code=201)
def create_category(
    category_in: CategoryCreate,  # ← Pydantic validates this
    user_id: UUID = Depends(get_current_user_id),
):
    # STEP 1: Convert schema to dict
    data = category_in.model_dump()  # Schema → Dict

    # STEP 2: Call service with dict
    category = service.create_category(data, user_id)  # Returns ORM

    # STEP 3: Convert ORM back to schema
    return Category.from_orm(category)  # ORM → Schema
```

---

### 2. Service Layer (Works with Dicts)

**Responsibilities:**

- Receive dicts from router
- Add business logic fields (user_id, timestamps, etc.)
- Validate business rules
- Pass dicts to repository
- Return ORM objects

**Pattern:**

```python
def create_category(self, data: dict, user_id: UUID) -> UserCategory:
    # STEP 1: Add extra fields to dict
    data["user_id"] = user_id

    # STEP 2: Validate business rules (work with dict)
    if self.repository.check_duplicate_name(data["name"], ...):
        raise HTTPException(status_code=409, detail="Duplicate")

    # STEP 3: Pass dict to repository
    return self.repository.create_category(data)  # Returns ORM
```

---

### 3. Repository Layer (Converts Dict to ORM)

**Responsibilities:**

- Receive dicts from service
- Convert dicts to ORM objects
- Perform database operations
- Return ORM objects

**Pattern:**

```python
def create_category(self, data: dict) -> UserCategory:
    # STEP 1: Unpack dict to create ORM
    category = UserCategory(**data)  # Dict → ORM

    # STEP 2: Database operations
    self.db.add(category)
    self.db.commit()
    self.db.refresh(category)

    # STEP 3: Return ORM
    return category
```

---

## ✅ Complete CRUD Examples

### CREATE Pattern

```python
# ========== ROUTER ==========
@router.post("", response_model=Category, status_code=201)
def create_category(
    category_in: CategoryCreate,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    service = CategoryService(db)
    data = category_in.model_dump()  # Schema → Dict
    category = service.create_category(data, user_id)
    return Category.from_orm(category)  # ORM → Schema


# ========== SERVICE ==========
def create_category(self, data: dict, user_id: UUID) -> UserCategory:
    data["user_id"] = user_id  # Add extra fields

    # Validation
    if self.repository.check_duplicate_name(data["name"], ...):
        raise HTTPException(status_code=409, detail="Duplicate")

    return self.repository.create_category(data)


# ========== REPOSITORY ==========
def create_category(self, data: dict) -> UserCategory:
    category = UserCategory(**data)  # Dict → ORM
    self.db.add(category)
    self.db.commit()
    self.db.refresh(category)
    return category
```

---

### UPDATE Pattern

```python
# ========== ROUTER ==========
@router.patch("/{category_id}", response_model=Category)
def update_category(
    category_id: UUID,
    update_in: CategoryUpdate,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    service = CategoryService(db)
    data = update_in.model_dump(exclude_unset=True)  # Only changed fields!
    category = service.update_category(category_id, data, user_id)
    return Category.from_orm(category)


# ========== SERVICE ==========
def update_category(self, category_id: UUID, data: dict, user_id: UUID) -> UserCategory:
    # Check exists
    category = self.repository.get_category_by_id(category_id, user_id)
    if not category:
        raise HTTPException(status_code=404, detail="Not found")

    # Validate changes (only validate what's changing)
    if "name" in data and data["name"] != category.name:
        if self.repository.check_duplicate_name(data["name"], ...):
            raise HTTPException(status_code=409, detail="Duplicate")

    # Pass dict to repository (NO MERGING NEEDED!)
    return self.repository.update_category(category_id, user_id, data)


# ========== REPOSITORY ==========
def update_category(self, category_id: UUID, user_id: UUID, data: dict) -> UserCategory:
    category = self.db.query(UserCategory).filter(
        UserCategory.id == category_id,
        UserCategory.user_id == user_id
    ).first()

    # Update fields from dict
    for key, value in data.items():
        setattr(category, key, value)

    self.db.commit()
    self.db.refresh(category)
    return category
```

---

### READ Pattern

```python
# ========== ROUTER ==========
@router.get("/{category_id}", response_model=Category)
def get_category(
    category_id: UUID,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    service = CategoryService(db)
    category = service.get_category_by_id(category_id, user_id)
    if not category:
        raise HTTPException(status_code=404, detail="Not found")
    return Category.from_orm(category)  # ORM → Schema


# ========== SERVICE ==========
def get_category_by_id(self, category_id: UUID, user_id: UUID) -> Optional[UserCategory]:
    return self.repository.get_category_by_id(category_id, user_id)


# ========== REPOSITORY ==========
def get_category_by_id(self, category_id: UUID, user_id: UUID) -> Optional[UserCategory]:
    return self.db.query(UserCategory).filter(
        UserCategory.id == category_id,
        UserCategory.user_id == user_id
    ).first()
```

---

### DELETE Pattern

```python
# ========== ROUTER ==========
@router.delete("/{category_id}", status_code=204)
def delete_category(
    category_id: UUID,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    service = CategoryService(db)
    success = service.delete_category(category_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Not found")
    return None  # 204 No Content


# ========== SERVICE ==========
def delete_category(self, category_id: UUID, user_id: UUID) -> bool:
    # Validation (e.g., check if category is in use)
    # ...

    return self.repository.soft_delete_category(category_id, user_id)


# ========== REPOSITORY ==========
def soft_delete_category(self, category_id: UUID, user_id: UUID) -> bool:
    category = self.db.query(UserCategory).filter(
        UserCategory.id == category_id,
        UserCategory.user_id == user_id
    ).first()

    if not category:
        return False

    category.is_active = False
    self.db.commit()
    return True
```

---

## 🎯 Quick Reference

| Conversion                  | Code                                    | Where                    |
| --------------------------- | --------------------------------------- | ------------------------ |
| **Schema → Dict**           | `schema.model_dump()`                   | Router → Service         |
| **Schema → Dict (partial)** | `schema.model_dump(exclude_unset=True)` | Router → Service (PATCH) |
| **Dict → ORM (create)**     | `Model(**dict)`                         | Repository (create)      |
| **Dict → ORM (update)**     | `setattr(orm, key, val)`                | Repository (update)      |
| **ORM → Schema**            | `Schema.from_orm(orm)`                  | Service → Router         |

---

## ⚠️ Common Mistakes

### ❌ WRONG: Trying to Spread ORM Objects

```python
# DON'T DO THIS!
category = self.repository.get_category_by_id(id, user_id)  # ORM object
data = {**category, **update_data}  # TypeError: 'UserCategory' object is not a mapping
```

**Why it fails:** ORM objects are NOT dictionaries. You can't use `**` on them.

---

### ❌ WRONG: Merging Data in Service Layer

```python
# DON'T DO THIS!
category = self.repository.get_category_by_id(id, user_id)
data = {
    "name": category.name,
    "parent_id": category.parent_id,
    **update_data
}
return self.repository.update_category(id, user_id, data)
```

**Why it's wrong:** Repository already handles partial updates with `setattr()`. You're duplicating work!

---

### ❌ WRONG: Forgetting `exclude_unset=True` on PATCH

```python
# DON'T DO THIS!
data = update_in.model_dump()  # Missing exclude_unset=True

# User sends: {"name": "New Name"}
# data becomes: {"name": "New Name", "parent_id": None, "display_order": None}
# ❌ This would set parent_id to None (unwanted!)
```

**Fix:**

```python
# DO THIS!
data = update_in.model_dump(exclude_unset=True)

# User sends: {"name": "New Name"}
# data becomes: {"name": "New Name"}
# ✅ Only updates the name field!
```

---

### ❌ WRONG: Converting ORM to Dict Manually

```python
# DON'T DO THIS!
category = self.repository.get_category_by_id(id, user_id)
data = {
    "id": category.id,
    "name": category.name,
    "parent_id": category.parent_id,
    # ... tedious and error-prone
}
```

**Why it's wrong:** You don't need to! Just return the ORM object and let the router convert it:

```python
# DO THIS!
category = self.repository.get_category_by_id(id, user_id)
return category  # Router will call Category.from_orm(category)
```

---

## 📝 When to Use `**` (Spread Operator)

### ✅ Dict → ORM (Create New Object)

```python
data = {"name": "Housing", "user_id": user_id}
category = UserCategory(**data)  # Unpack dict to ORM constructor
```

### ✅ Dict → Dict (Merge Dictionaries)

```python
base_data = {"user_id": user_id}
input_data = {"name": "Housing"}
merged = {**base_data, **input_data}  # {"user_id": ..., "name": "Housing"}
```

### ❌ ORM → Dict (Doesn't Work!)

```python
category = UserCategory.query.first()  # ORM object
merged = {**category, **update_data}  # TypeError!
```

---

## 🎯 The Golden Rules

1. **Router works with Schemas** (Pydantic validation)
2. **Service works with Dicts** (business logic)
3. **Repository works with ORMs** (database operations)
4. **Never spread (`**`) an ORM object\*\* - only spread dicts!
5. **Use `exclude_unset=True` for PATCH** - only update changed fields
6. **Let repository handle merging** - don't merge in service layer

---

## 🔄 Data Flow Diagram

```
Frontend (JSON)
    ↓
Router receives HTTP request
    ↓
FastAPI validates → Pydantic Schema
    ↓
schema.model_dump() → Dict
    ↓
Service receives dict
    ↓
Add fields, validate → Dict
    ↓
Repository receives dict
    ↓
Model(**dict) → ORM object
    ↓
Database saves ORM
    ↓
Repository returns ORM
    ↓
Service returns ORM
    ↓
Router converts → Schema.from_orm(orm)
    ↓
FastAPI serializes → JSON
    ↓
Frontend receives JSON
```

---

## 💡 Pro Tips

### Tip 1: Service Layer Returns ORM, Router Converts to Schema

```python
# ✅ Good pattern
# Service
def create_category(...) -> UserCategory:  # Returns ORM
    return self.repository.create_category(data)

# Router
category = service.create_category(...)  # ORM
return Category.from_orm(category)  # Convert here
```

### Tip 2: Use Type Hints to Stay Clear

```python
def create_category(self, data: dict, user_id: UUID) -> UserCategory:
    #                       ↑ Dict in         ↑ ORM out
```

### Tip 3: Validate Only Changed Fields on Update

```python
# Only check duplicate if name is changing
if "name" in update_data and update_data["name"] != category.name:
    if self.repository.check_duplicate_name(...):
        raise HTTPException(...)
```

---

## 📚 Related Guides

- [ORM vs Schema Cheatsheet](./orm-vs-schema-cheatsheet.md)
- [Pydantic Schema Naming Convention](../CLAUDE.md#pydantic-schema-naming-convention)

---

**Remember:** When in doubt, follow this guide! Copy the patterns directly for consistency. 🚀
