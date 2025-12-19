# Balance Points System - Core Concept

## 🎯 The Problem We're Solving

**Scenario:** You have a bank account and want to see how your balance changed over time.

**Challenge:**
- Transactions happen on specific days
- But you want to know your balance for EVERY day (even days without transactions)
- When you add old transactions, you need to recalculate everything from that point forward

---

## 💡 The Solution: Daily Balance Timeline

### **Core Concept:**
**Every account gets ONE balance point for EACH day.**

Think of it like a daily diary entry:
```
Jan 1: Balance was $1000
Jan 2: Balance was $1000
Jan 3: Balance was $950
Jan 4: Balance was $950
Jan 5: Balance was $1450
```

### **How It Works:**

#### **Step 1: Account Creation**
```
User creates account with $1000 initial balance
→ System creates first BalancePoint:
  - date: Jan 1, 2025
  - balance: $1000
  - has_transactions: false (just initial balance)
  - timeline_status: "current"
```

#### **Step 2: Days Without Transactions (Gap Filling)**
```
Jan 2 - no transactions happened
→ System CLONES yesterday's balance:
  - date: Jan 2, 2025
  - balance: $1000 (copied from Jan 1)
  - has_transactions: false
  - timeline_status: "current"
```

#### **Step 3: Days WITH Transactions**
```
Jan 3 - User bought coffee for $50
→ System CALCULATES new balance:
  - date: Jan 3, 2025
  - balance: $950 ($1000 - $50)
  - has_transactions: true (had a transaction!)
  - timeline_status: "current"
```

#### **Step 4: Historical Transactions (The Hard Part)**
```
User adds OLD transaction on Jan 2 for $100
→ Problem: Jan 3, 4, 5 balances are now WRONG!
→ Solution: Mark timeline as "updating" and recalculate in background:

  Jan 2: $900 ($1000 - $100) ← recalculated
  Jan 3: $850 ($900 - $50)   ← recalculated
  Jan 4: $850                ← recalculated
  Jan 5: $1350               ← recalculated

  timeline_status: "updating" → then "current" when done
```

---

## 🗂️ Database Structure

Each `BalancePoint` record stores:

| Field | Type | Purpose | Example |
|-------|------|---------|---------|
| `id` | UUID | Unique identifier | `a1b2c3...` |
| `account_id` | UUID | Which account | `xyz789...` |
| `date` | Date | Which specific day | `2025-01-03` |
| `balance` | Decimal(15,2) | Balance on that day | `950.00` |
| `has_transactions` | Boolean | Did transactions happen? | `true` |
| `timeline_status` | String | Is it current/updating/failed? | `"current"` |
| `created_at` | DateTime | When record created | `2025-01-03 10:00:00` |
| `updated_at` | DateTime | When last updated | `2025-01-03 10:00:00` |

**Unique Constraint:** One balance point per account per day!
```
UNIQUE(account_id, date)
```

---

## 🔄 The Three Timeline States

### **1. "current"** ✅
- Balance is accurate and up-to-date
- User can trust this data
- Normal state

### **2. "updating"** ⏳
- System is recalculating balances in background
- User added old transaction or made changes
- Show loading indicator to user

### **3. "failed"** ❌
- Something went wrong during calculation
- User should retry or contact support
- Needs manual intervention

---

## 📏 Business Rules

### **2-Year Limit**
- Only track balances for last 730 days (2 years)
- Reject transactions older than 2 years
- Why? Performance + data management

### **Gap Filling**
- If no transactions on a day → clone previous day
- Ensures continuous timeline (no missing days)
- `has_transactions = false` marks cloned days

### **Automatic Calculation**
- Users DON'T manually enter balance points
- System calculates from transactions
- Exception: Initial balance when creating account

---

## 🎬 Real-World Example

**Mario's Checking Account:**

```
Timeline:
├─ Jan 1  [$1000] ← Account created with initial balance
├─ Jan 2  [$1000] ← No transactions (gap filled)
├─ Jan 3  [$950]  ← Coffee purchase ($-50)
├─ Jan 4  [$950]  ← No transactions (gap filled)
├─ Jan 5  [$1450] ← Paycheck deposited ($+500)
└─ Jan 6  [$1450] ← No transactions (gap filled)

Database has 6 BalancePoint records (one per day)
```

**What happens if you add old transaction?**
```
User adds: Jan 2 - Groceries $100

System:
1. Marks timeline_status = "updating"
2. Recalculates Jan 2 → Jan 6
3. Updates all 5 balance points
4. Marks timeline_status = "current"
```

---

## 🎨 Frontend User Experience

**What user sees:**

**Normal state:**
```
📊 Balance Timeline
Jan 1: $1000
Jan 2: $1000
Jan 3: $950
Jan 5: $1450
```

**Updating state:**
```
📊 Balance Timeline (Updating...)
⏳ Recalculating balances...
[Refresh Button]
```

---

## 🏗️ Why This Architecture?

### **Advantages:**
1. ✅ **Fast queries** - No need to calculate on the fly
2. ✅ **Continuous timeline** - No missing days
3. ✅ **Historical support** - Can add old transactions
4. ✅ **User feedback** - Status shows when updating
5. ✅ **Scalable** - Pre-calculated data is fast

### **Trade-offs:**
1. ⚠️ **Storage** - More database records (one per day per account)
2. ⚠️ **Complexity** - Background recalculation needed
3. ⚠️ **Eventual consistency** - Brief delay when updating

---

## 📖 Where This Fits in the Codebase

```
Models (models.py)
  ↓ defines database structure
Schemas (schemas.py)
  ↓ defines API request/response format
Repository (repository.py)
  ↓ database queries (get/save balance points)
Service (service.py)
  ↓ business logic (calculate balances, handle updates)
Router (router.py)
  ↓ API endpoints (what frontend calls)
```

---

## 🔗 Related Documentation

- **Implementation Plan**: `/docs/plans/balance-points-refactoring.md`
- **Mentoring Approach**: `/docs/guides/claude-mentoring-approach.md`
- **Project Instructions**: `/CLAUDE.md`

---

## 📝 Implementation Phases

### **Phase 1: Database Foundation** (Current)
- Task 1.1: Update BalancePoint model ✅
- Task 1.2: Validation & Business Rules ⏳

### **Phase 2: Repository Layer**
- CRUD operations
- Status management
- Gap filling operations

### **Phase 3: Service Layer**
- Timeline calculation
- Background job management
- Historical transaction handling

### **Phase 4-6: API, Background Jobs, Testing**
- Router endpoints
- Job processing
- Documentation

---

**Last Updated:** 2025-11-20
**Status:** Active Development - Phase 1
