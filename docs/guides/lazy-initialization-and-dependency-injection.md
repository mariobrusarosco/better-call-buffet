# Deep Dive: Lazy Initialization & Dependency Injection

**Context:** These concepts were learned while fixing a Settings validation bug caused by upgrading from Poetry 1.x to 2.x, which changed when pydantic-settings validates configuration.

**Date:** December 2025
**Related Fix:** [Settings lru_cache pattern implementation](../../app/core/config.py)

---

## Table of Contents
1. [Lazy Initialization (Deeper)](#lazy-initialization-deeper)
2. [Dependency Injection (Deeper)](#dependency-injection-deeper)
3. [Combining Both Patterns](#combining-lazy--di-your-settings)
4. [Key Takeaways](#key-differences-summary)

---

## Lazy Initialization (Deeper)

### The Core Concept

**Execution Timeline is everything:**

```python
# EAGER (immediate)
settings = Settings()  # <-- Runs RIGHT NOW when Python reads this line

# File: app/main.py
from app.core.config import settings  # ← Settings() runs HERE during import
```

**What happens during import:**
```
1. Python imports app/core/config.py
2. Python reads line: settings = Settings()
3. Settings.__init__() runs
4. Pydantic validates ALL 16 fields
5. Missing env var? CRASH immediately
```

**VS Lazy:**
```python
@lru_cache
def get_settings():
    return Settings()  # <-- Only runs when YOU call this function

# File: app/main.py
from app.core.config import get_settings  # ← Nothing happens yet!

# Later...
settings = get_settings()  # ← Settings() runs HERE, not during import
```

---

### Why This Matters (Real Example From Your Bug)

**The Problem Timeline:**

```python
# migrations/env.py (OLD CODE)
from app.core.config import settings  # ← Step 1: Import runs

# What Python does:
# → Opens config.py
# → Sees: settings = Settings()
# → Executes Settings()
# → Pydantic: "Where's OPENAI_API_KEY?"
# → CRASH! ❌
```

**The CI had NO env vars set** except `DATABASE_URL`, so Settings validation failed during import.

**The Fix:**

```python
# migrations/env.py (NEW CODE)
# No import of settings at all! ✅

# app/main.py (NEW CODE)
from app.core.config import get_settings  # ← Import is safe, no execution

settings = get_settings()  # ← NOW it validates
# By this point, .env file is loaded, all vars present ✅
```

---

### The Power of Control

**Lazy gives you CONTROL over WHEN things happen:**

```python
# Eager - you have NO control
settings = Settings()  # Runs during import, can't stop it

# Lazy - you control WHEN
def get_settings():
    return Settings()

# In tests:
def test_something():
    os.environ['DATABASE_URL'] = 'test-db'  # Set env vars FIRST
    settings = get_settings()  # THEN validate
    # Works! ✅
```

**With eager, tests fail because Settings validates BEFORE you can set test env vars.**

---

### Another Real-World Example

**Database Connection (Common Pattern):**

```python
# BAD - Eager
db = Database(connection_string)  # Connects NOW
# Problem: What if app isn't ready? No env vars? Not in right environment?

# GOOD - Lazy
def get_db():
    if not hasattr(get_db, '_connection'):
        get_db._connection = Database(connection_string)
    return get_db._connection

# Connect only when FIRST used
db = get_db()  # ← Connection happens HERE
```

---

## Dependency Injection (Deeper)

### The Problem It Solves

**Without DI (Manual Management):**

```python
# Every function manually creates what it needs
def create_user(username: str):
    db = get_database()  # ← You have to remember this
    settings = get_settings()  # ← And this
    logger = get_logger()  # ← And this

    # Your actual logic
    user = User(username=username)
    db.save(user)
```

**Problems:**
- 😣 Repetitive (every function does this)
- 😣 Easy to forget a dependency
- 😣 Hard to test (mocking is painful)
- 😣 Tight coupling (function knows HOW to get dependencies)

---

### With DI (Framework Manages)

```python
# FastAPI injects dependencies FOR you
@app.post("/users")
def create_user(
    username: str,
    db: Database = Depends(get_database),
    settings: Settings = Depends(get_settings),
    logger: Logger = Depends(get_logger)
):
    # Your actual logic - dependencies already here!
    user = User(username=username)
    db.save(user)
```

**What FastAPI does behind the scenes:**

```python
# When request comes in, FastAPI:
1. Sees you need 'db'
2. Calls get_database() for you
3. Sees you need 'settings'
4. Calls get_settings() for you
5. Passes them to your function
6. You write business logic only!
```

---

### The Power: Testing

**Without DI (Painful):**

```python
def test_create_user():
    # How do you mock get_database() that's INSIDE the function?
    # You can't easily! Need monkey patching, globals, etc.
    create_user("Alice")  # ← Can't control what DB it uses
```

**With DI (Easy):**

```python
def test_create_user():
    # Override the dependency with a fake
    app.dependency_overrides[get_database] = lambda: FakeDatabase()

    # Now your function uses FakeDatabase automatically!
    create_user("Alice")  # ← Uses fake DB, no real DB needed ✅
```

---

## Combining Lazy + DI (Your Settings)

**The Perfect Pattern:**

```python
# 1. Lazy initialization
@lru_cache
def get_settings() -> Settings:
    return Settings()  # Only creates once when first called

# 2. Dependency Injection usage
@app.get("/info")
def info(settings: Settings = Depends(get_settings)):
    return {"api_key": settings.OPENAI_API_KEY}
```

**What happens when request comes:**

```
Request → FastAPI sees Depends(get_settings)
       → Calls get_settings()
       → First time? Creates Settings() and caches it
       → Second time? Returns cached instance
       → Passes to your function
       → You use it without worrying about HOW it was created
```

---

### Real-World Analogy

**Without DI (You're a Chef):**
```
Boss: "Make a pizza"
You: "Where's the dough?"
Boss: "Go to the pantry and get it yourself"
You: "Where's the sauce?"
Boss: "Make it from tomatoes in the garden"
You: "Where's the cheese?"
Boss: "Get it from the fridge"

(You spend 80% of time gathering ingredients)
```

**With DI (You're a Chef):**
```
Boss: "Make a pizza"
*Ingredients appear on your counter*
You: *Just makes the pizza*

(You spend 100% of time on your actual job)
```

---

### Why FastAPI Recommends This

**From their docs:**

> "Having a function for settings allows you to:
> - Only load settings when needed (lazy)
> - Cache them with @lru_cache (singleton)
> - Override them in tests (dependency injection)
> - Keep code clean (no global state)"

---

## Key Differences Summary

### Lazy vs Eager

| **Aspect** | **Eager** | **Lazy** |
|------------|-----------|----------|
| **When runs** | Import time | First call time |
| **Control** | None (automatic) | Full (explicit) |
| **Testing** | Hard (already executed) | Easy (control when) |
| **Failures** | Immediate crash | Delayed until needed |

### Manual vs Dependency Injection

| **Aspect** | **Manual** | **DI** |
|------------|-----------|----------|
| **Get dependencies** | You call functions | Framework calls for you |
| **Boilerplate** | Lots of repetition | Declarative (Depends) |
| **Testing** | Hard (internals) | Easy (override) |
| **Coupling** | Tight (knows HOW) | Loose (declares WHAT) |

---

## The "Aha!" Moment

**Your bug taught you this:**

```
Migration imports config → Config validates → Missing env vars → CRASH
```

**Fixed by understanding:**

1. **Lazy:** "Don't validate until actually needed"
2. **DI:** "Let the framework manage when Settings is created"
3. **Separation:** "Migrations don't need Settings at all"

This is **professional-grade architecture** - not just "it works", but "it works elegantly and testably."

---

## Additional Concepts Learned

### 1. **Singleton Pattern**

**What it is:** Ensuring only ONE instance of a class exists in your entire application.

**Why we used it:**
```python
@lru_cache  # Creates singleton behavior
def get_settings() -> Settings:
    return Settings()  # Only runs ONCE
```

**Real-world analogy:** Like having one main office key that everyone shares vs. everyone making their own copy.

**When to use:**
- ✅ Configuration/Settings (like we did)
- ✅ Database connection pools
- ✅ Logger instances
- ✅ Caching systems
- ❌ User objects (each user should have their own)

---

### 2. **Separation of Concerns**

**The mistake:** Migrations imported full app config when they only needed DB connection.

**The principle:** Each part of your system should only know about what it NEEDS.

```
Migrations need:     DATABASE_URL only
App runtime needs:   All 16 config fields
```

**Why it matters:**
- Easier testing (smaller dependencies)
- Clearer code (obvious what each part needs)
- Better maintainability

---

### 3. **Module-level Side Effects (Anti-pattern)**

**Bad:**
```python
settings = Settings()  # Side effect at module import time
```

**Good:**
```python
def get_settings():
    return Settings()  # No side effects, explicit call
```

**Why module-level is bad:**
- Hard to test
- Import order matters
- Can't control WHEN it runs
- Hides dependencies

---

### 4. **Breaking Changes in Dependencies**

**What happened:** Poetry 1.x → 2.x upgraded pydantic-settings, which changed when validation happens.

**Lesson:** Version upgrades aren't "free" - they can change behavior.

**Best practices:**
- Pin critical dependencies
- Read changelogs before upgrading
- Test after dependency updates
- Understand what your tools do under the hood

---

## References

- [FastAPI Settings Documentation](https://fastapi.tiangolo.com/advanced/settings/)
- [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Python lru_cache Documentation](https://docs.python.org/3/library/functools.html#functools.lru_cache)
- [Dependency Injection Pattern](https://en.wikipedia.org/wiki/Dependency_injection)

---

## Related Files in This Project

- `app/core/config.py` - Implementation of lazy-loaded settings with `@lru_cache`
- `app/main.py` - Usage of `get_settings()` at module level
- `app/core/dependencies.py` - Dependency injection examples with `Depends()`
- `migrations/env.py` - Example of NOT importing settings (separation of concerns)

---

**Remember:** Good architecture makes problems easier to fix. We didn't have to rewrite the app - we just changed HOW settings load. That's the power of well-designed patterns.
