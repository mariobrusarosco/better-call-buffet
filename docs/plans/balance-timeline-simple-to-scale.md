# Balance Timeline Implementation Plan

## Philosophy: Start Simple, Measure, Evolve

---

## 🎯 Project Goals

**Core Requirement:** Display account balance timeline for any date range
**Audit Requirement:** Ability to answer "What did user see on Jan 15?"
**Scale Target:** Thousands of users, ~100 transactions/month/user
**Learning Goal:** Understand fundamentals → caching → pre-calculation evolution

---

## 🏗️ Architecture Decision: Transaction-First Approach

**Source of Truth:** Transaction history (immutable audit trail)
**Balance Calculation:** On-demand from transactions (with caching layer)
**Evolution Path:** Simple → Cached → Pre-calculated (only if needed)

### Why This Approach?

✅ **Audit trail built-in** - Transactions ARE the historical record
✅ **Simple to implement** - No background jobs initially
✅ **Fast to ship** - See results quickly
✅ **Learn fundamentals** - Queries, indexes, caching
✅ **Easy migration** - Can add pre-calculation later with zero pain

---

## 📊 Phase 1: Foundation - Transaction Query Layer

**Goal:** Build efficient transaction querying with proper indexing

### Task 1.1: Transaction Repository Methods ⏳

**File:** `app/domains/transactions/repository.py`

Implement these methods:

```python
def get_transactions_for_timeline(
    self,
    account_id: UUID,
    start_date: date,
    end_date: date
) -> List[Transaction]:
    """
    Get all transactions for an account in date range.
    Ordered by date ASC for timeline calculation.
    """
    pass

def get_initial_balance(self, account_id: UUID, before_date: date) -> Decimal:
    """
    Calculate account balance before a specific date.
    Used as starting point for timeline calculation.
    """
    pass

def get_transaction_count(self, account_id: UUID) -> int:
    """
    Get total transaction count for performance testing.
    """
    pass
```

**Learning Objectives:**

- Understanding date range queries
- Query ordering for performance
- Aggregation queries (for initial balance)

### Task 1.2: Database Indexing 📚

**File:** Create migration for transaction indexes

```sql
-- Critical index for timeline queries
CREATE INDEX idx_transactions_account_date
ON transactions(account_id, date DESC);

-- Index for initial balance calculation
CREATE INDEX idx_transactions_account_date_amount
ON transactions(account_id, date, amount);
```

**Learning Objectives:**

- Understanding compound indexes
- Query performance optimization
- Index selection strategies

**Validation:**

- [ ] Run EXPLAIN ANALYZE on timeline query
- [ ] Verify index is being used
- [ ] Benchmark query time with 1,200+ transactions

---

## 📊 Phase 2: Service Layer - Balance Calculation Logic

**Goal:** Calculate balance timeline from transaction history

### Task 2.1: Timeline Calculation Service 🧮

**File:** `app/domains/balance_points/service.py`

Implement:

```python
def calculate_balance_timeline(
    self,
    account_id: UUID,
    start_date: date,
    end_date: date,
    user_id: UUID
) -> List[BalancePoint]:
    """
    Calculate daily balance timeline from transactions.

    Algorithm:
    1. Get initial balance (before start_date)
    2. Get all transactions in range
    3. For each day in range:
       - Apply that day's transactions
       - Record balance for the day
    4. Return timeline
    """
    pass

def get_balance_at_date(
    self,
    account_id: UUID,
    as_of_date: date,
    user_id: UUID
) -> Decimal:
    """
    Calculate balance as it was on a specific historical date.
    (Audit trail: "What did user see on Jan 15?")
    """
    pass
```

**Learning Objectives:**

- Running balance calculation algorithms
- Date range iteration
- Transaction impact calculation
- Historical point-in-time queries

### Task 2.2: Gap Filling Logic 🔗

**File:** `app/domains/balance_points/service.py`

```python
def _fill_timeline_gaps(
    self,
    transactions: List[Transaction],
    start_date: date,
    end_date: date,
    initial_balance: Decimal
) -> List[dict]:
    """
    Create continuous timeline with daily balance points.
    Days without transactions copy previous day's balance.
    """
    pass
```

**Learning Objectives:**

- Efficient iteration strategies
- Gap detection algorithms
- Memory-efficient timeline building

---

## 📊 Phase 3: API Layer - Expose Endpoints

**Goal:** Create user-facing API endpoints

### Task 3.1: Balance Timeline Router 🛣️

**File:** `app/domains/balance_points/router.py`

```python
@router.get("/accounts/{account_id}/balance-timeline")
def get_balance_timeline(
    account_id: UUID,
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_user: User = Depends(get_current_user),
    service: BalancePointService = Depends()
) -> List[BalancePoint]:
    """
    Get daily balance timeline for date range.
    """
    pass

@router.get("/accounts/{account_id}/balance-at-date")
def get_balance_at_date(
    account_id: UUID,
    as_of_date: date = Query(...),
    current_user: User = Depends(get_current_user),
    service: BalancePointService = Depends()
) -> BalanceAtDateResponse:
    """
    Get balance as it was on a specific date (audit trail).
    """
    pass
```

**Learning Objectives:**

- RESTful API design
- Query parameter validation
- Response schema design
- Authorization patterns

### Task 3.2: Response Schemas 📋

**File:** `app/domains/balance_points/schemas.py`

```python
class BalancePoint(BaseModel):
    """Timeline point - not stored, calculated on-demand"""
    date: date
    balance: Decimal
    has_transactions: bool  # Did transactions occur this day?

class BalanceAtDateResponse(BaseModel):
    """Historical balance response"""
    account_id: UUID
    as_of_date: date
    balance: Decimal
    transaction_count: int  # How many transactions influenced this
```

---

## 📊 Phase 4: Performance Measurement & Optimization

**Goal:** Measure actual performance, identify bottlenecks

### Task 4.1: Performance Benchmarking 📈

**File:** `tests/performance/test_timeline_performance.py`

Create tests:

```python
def test_timeline_performance_100_transactions():
    """Measure query time with 100 transactions (1 month)"""
    pass

def test_timeline_performance_1200_transactions():
    """Measure query time with 1,200 transactions (1 year)"""
    pass

def test_timeline_performance_2400_transactions():
    """Measure query time with 2,400 transactions (2 years)"""
    pass
```

**Success Criteria:**

- [ ] < 100ms for 1 month (100 transactions)
- [ ] < 200ms for 1 year (1,200 transactions)
- [ ] < 500ms for 2 years (2,400 transactions)

**Learning Objectives:**

- Performance testing methodology
- Benchmarking best practices
- Identifying bottlenecks with data

### Task 4.2: Query Optimization 🔧

If benchmarks fail, optimize:

- [ ] Review EXPLAIN ANALYZE output
- [ ] Add missing indexes
- [ ] Optimize query structure
- [ ] Consider query result pagination

**Learning Objectives:**

- Reading query execution plans
- Index tuning
- Query optimization techniques

---

## 📊 Phase 5: Caching Layer (If Needed)

**Goal:** Add caching if Phase 4 shows performance issues

### Task 5.1: In-Memory Caching 🗄️

**File:** `app/core/cache.py`

```python
from functools import lru_cache, wraps
from datetime import datetime, timedelta

def cache_timeline(ttl_seconds: int = 300):
    """
    Cache timeline results for 5 minutes.
    Invalidate on new transactions.
    """
    pass
```

**Usage:**

```python
@cache_timeline(ttl_seconds=300)
def calculate_balance_timeline(self, account_id, start, end, user_id):
    # Same calculation, now cached!
    pass
```

**Learning Objectives:**

- Caching strategies (TTL, invalidation)
- Cache key design
- When to cache vs when to calculate

### Task 5.2: Cache Invalidation 🔄

```python
def invalidate_timeline_cache(account_id: UUID):
    """
    Clear cached timeline when new transaction added.
    """
    pass
```

**Learning Objectives:**

- Cache invalidation patterns
- Balancing freshness vs performance

---

## 📊 Phase 6: Pre-Calculation Migration (Only If Needed!)

**Goal:** Migrate to pre-calculated approach if caching isn't enough

**Trigger:** Benchmarks show > 500ms even with caching

### Task 6.1: Activate Balance Points Table 💾

The table already exists (from Phase 1)! Just start using it.

**File:** `app/domains/balance_points/repository.py`

```python
def create_balance_point(self, balance_point_data: dict) -> BalancePoint:
    """We already built this! Just activate it."""
    # Already implemented!
    pass

def get_balance_points(
    self,
    account_id: UUID,
    start_date: date,
    end_date: date
) -> List[BalancePoint]:
    """Query pre-calculated balance points"""
    pass
```

### Task 6.2: Background Calculation Jobs 🔄

**File:** `app/domains/balance_points/jobs.py`

```python
def recalculate_balance_timeline_async(account_id: UUID):
    """
    Background job to pre-calculate and save balance points.
    Triggered when transaction is added.
    """
    pass
```

**Learning Objectives:**

- Background job patterns
- Async processing
- Job queue management

### Task 6.3: Service Layer Migration 🔀

**File:** `app/domains/balance_points/service.py`

```python
def get_balance_timeline(self, account_id, start, end, user_id):
    """
    NEW: Check if pre-calculated data exists
    If yes: Return from balance_points table
    If no: Calculate on-demand (fallback)
    """
    balance_points = self.repo.get_balance_points(account_id, start, end)

    if balance_points:
        return balance_points  # Pre-calculated!
    else:
        return self._calculate_on_demand(account_id, start, end)  # Fallback
```

**Key:** Router doesn't change! Same API, different implementation.

---

## 📊 Testing Strategy

### Unit Tests

```python
tests/domains/balance_points/
├── test_repository.py         # Query methods
├── test_service.py            # Calculation logic
├── test_timeline_gaps.py      # Gap filling
└── test_audit_trail.py        # Historical queries
```

### Integration Tests

```python
tests/integration/
├── test_timeline_api.py       # End-to-end API tests
├── test_transaction_impact.py # Adding transaction updates timeline
└── test_cache_invalidation.py # Cache works correctly
```

### Performance Tests

```python
tests/performance/
├── test_query_performance.py  # Benchmark queries
├── test_timeline_calculation.py
└── test_with_real_data.py     # Test with 1,200+ transactions
```

---

## 📋 Checklist Summary

### ✅ Phase 1: Foundation

- [x] Transaction repository query methods
- [x] Database indexes for timeline queries
- [ ] Performance validation (EXPLAIN ANALYZE)

### ✅ Phase 2: Calculation

- [x] Timeline calculation service
- [x] Gap filling logic
- [x] Historical balance query (audit trail)

### ✅ Phase 3: API

- [x] Timeline endpoint
- [x] Historical balance endpoint
- [x] Response schemas

### ✅ Phase 4: Measurement

- [ ] Performance benchmarks
- [ ] Query optimization
- [ ] Document actual performance

### ⏸️ Phase 5: Caching (If needed)

- [ ] In-memory caching layer
- [ ] Cache invalidation logic
- [ ] Measure cache hit rates

### ⏸️ Phase 6: Pre-calculation (If needed)

- [ ] Activate balance_points table
- [ ] Background calculation jobs
- [ ] Migrate service layer (zero API changes!)

---

## 🎓 Learning Outcomes

By completing this plan, you'll learn:

1. **Database Fundamentals**

   - Query optimization
   - Index design and tuning
   - Understanding EXPLAIN ANALYZE

2. **Performance Engineering**

   - How to measure (before optimizing!)
   - Identifying bottlenecks with data
   - When complexity is justified

3. **Evolution Architecture**

   - Simple → Cached → Pre-calculated
   - Zero-downtime migrations
   - API stability during internal changes

4. **Enterprise Patterns**
   - Layer separation (Repository/Service/Router)
   - Caching strategies
   - Background job processing (if needed)

---

## 🚀 Success Metrics

**Phase 1-3 Complete:**

- ✅ Working timeline API
- ✅ Audit trail capability
- ✅ Shipped to users!

**Phase 4 Complete:**

- ✅ Measured performance with real data
- ✅ Know if optimization needed
- ✅ Data-driven decisions

**Phase 5+ (Optional):**

- ✅ Optimized only if needed
- ✅ Learned when complexity is justified

---

**Philosophy:** Build the simplest thing that works, measure it, optimize only what's proven slow!

**Last Updated:** 2025-12-13
**Status:** Active - Starting Phase 1
