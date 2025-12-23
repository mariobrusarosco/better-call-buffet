# 🚀 ORM vs Schema - 30 Second Cheatsheet

## The Rule
```
ORM Models = Database stuff (internal)
Pydantic Schemas = API stuff (external)
```

---

## Where Each Lives

| Layer | Uses | Returns |
|-------|------|---------|
| **Repository** | ORM | ORM |
| **Service** | ORM | ORM |
| **Router** | Schemas | Schemas |

---

## Router Pattern (Copy-Paste This)

```python
# INPUT: Pydantic validates request
# OUTPUT: response_model validates response

@router.post("", response_model=CategoryResponse, status_code=201)
def create_category(
    category_in: CategoryCreate,  # ← Input schema
    ...
):
    orm_object = service.create_category(...)  # Service returns ORM
    return CategoryResponse.from_orm(orm_object)  # Convert to schema


@router.get("", response_model=List[CategoryTreeNode])
def get_categories(...):
    tree = service.assemble_category_tree(...)  # Service returns schemas
    return tree  # Already schemas, just return
```

---

## Conversion Cheatsheet

```python
# Schema → Dict (for creating ORM)
data = schema.model_dump()  # or .dict() in Pydantic v1

# ORM → Schema (for API response)
schema = MySchema.from_orm(orm_model)

# FastAPI auto-converts if response_model is set
@router.get("", response_model=MySchema)
def endpoint():
    return orm_model  # FastAPI converts automatically!
```

---

## When to Convert

```
Service returns ORM ──→ Router converts to Schema ──→ FastAPI sends JSON
```

---

## Common Mistakes to Avoid

❌ **Don't return ORM from router without response_model**
```python
@router.get("")  # Missing response_model!
def get_categories(...):
    return service.get_all_categories(...)  # Returns ORM - exposes all fields!
```

✅ **Always use response_model**
```python
@router.get("", response_model=List[CategoryResponse])
def get_categories(...):
    categories = service.get_all_categories(...)  # ORM
    return [CategoryResponse.from_orm(c) for c in categories]  # Schemas
```

---

## Quick Decision Tree

```
Am I in the router?
  ├─ YES → Use Schemas + response_model
  └─ NO → Use ORM models
```

---

**Remember:** ORM stays internal, Schemas are your API contract! 🎯
