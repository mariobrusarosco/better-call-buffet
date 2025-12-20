# Transaction Editing - Core Concepts

## What is Updating vs Creating?

When you **create** a resource, you're adding something new:
```python
# Creating = "I want to add a new transaction"
POST /transactions
{
  "date": "2025-01-15",
  "amount": 100.00,
  "description": "Groceries"
}
```

When you **update** a resource, you're modifying something that already exists:
```python
# Updating = "I want to change an existing transaction"
PATCH /transactions/abc-123
{
  "description": "Groceries from Whole Foods"  # Fix the description
}
```

---

## PUT vs PATCH: Two Philosophies

### PUT - "Replace Everything"

**Philosophy:** Give me the COMPLETE new version, I'll replace the old one entirely.

**Example:**
```http
PUT /transactions/abc-123
{
  "date": "2025-01-15",
  "amount": 100.00,
  "description": "Updated",
  "category": "Food",
  "movement_type": "expense",
  "is_paid": true,
  "account_id": "xyz-789"
}
```

**What happens:**
1. Backend receives ALL fields
2. Backend replaces the ENTIRE transaction
3. If you forget a field → it becomes `null` or default value

**Analogy:** Rewriting an entire email from scratch

**Pros:**
- ✅ Simple to implement (just replace everything)
- ✅ Clear what the final state will be
- ✅ No ambiguity about what changed

**Cons:**
- ❌ Frontend must send ALL fields (even unchanged ones)
- ❌ Easy to accidentally clear fields you forgot to include
- ❌ More data over network
- ❌ Harder to use (must know all fields)

---

### PATCH - "Update Specific Fields"

**Philosophy:** Tell me ONLY what changed, I'll update just those fields.

**Example:**
```http
PATCH /transactions/abc-123
{
  "description": "Groceries from Whole Foods"
}
```

**What happens:**
1. Backend receives ONLY the field to change
2. Backend updates ONLY `description`
3. All other fields (date, amount, category) stay the same

**Analogy:** Using correction fluid on specific words in a document

**Pros:**
- ✅ Flexible - update 1 field or 10 fields
- ✅ Safer - can't accidentally clear fields
- ✅ Less data over network
- ✅ Frontend-friendly (only send what user edited)
- ✅ Better for mobile (smaller payloads)

**Cons:**
- ❌ More complex to implement (optional fields, validation)
- ❌ Less predictable (depends on what's sent)

---

## Our Decision: PATCH

**We're using PATCH for transactions because:**

1. **User Experience:** Users often want to fix just one thing
   - "Oops, I typed the wrong amount" → Change only `amount`
   - "I need to categorize this" → Change only `category`

2. **Mobile-Friendly:** Smaller payloads save bandwidth

3. **Safety:** Can't accidentally clear fields

4. **Flexibility:** Can update 1 field or all fields in same endpoint

---

## Partial Updates: Making Fields Optional

When using PATCH, all fields become **optional** (user picks what to update).

### Schema Design Pattern

**Create schema (all required):**
```python
class TransactionIn(BaseModel):
    date: datetime              # ✅ Required
    amount: Decimal             # ✅ Required
    description: str            # ✅ Required
    category: Optional[str]     # Optional
    account_id: Optional[UUID]  # Optional (XOR with credit_card_id)
```

**Update schema (all optional):**
```python
class TransactionUpdate(BaseModel):
    date: Optional[datetime] = None        # ❌ Optional - only update if provided
    amount: Optional[Decimal] = None       # ❌ Optional
    description: Optional[str] = None      # ❌ Optional
    category: Optional[str] = None         # ❌ Optional
    account_id: Optional[UUID] = None      # ❌ Optional
```

**Key difference:**
- Create: "You MUST provide date, amount, description"
- Update: "Provide ONLY the fields you want to change"

---

## The `exclude_unset` Pattern

**Problem:** How do we know if user wants to:
- Clear a field (set to `null`)
- Not change a field (leave as is)

**Example:**
```python
# User sends:
{
  "description": "Updated"
}

# We receive in Pydantic:
TransactionUpdate(
    description="Updated",
    amount=None,        # ← Did user want to clear amount? Or not change it?
    category=None,      # ← Same question!
)
```

**Solution:** `exclude_unset=True`

```python
# Get only fields that were actually sent
update_data = update_schema.model_dump(exclude_unset=True)

# Result:
{
  "description": "Updated"  # ✅ Only this field!
}
# amount and category are NOT in dict → we know not to touch them
```

**Explanation:**
- `exclude_unset=True` → Exclude fields that weren't provided in request
- Only fields user explicitly sent are in the dict
- Loop through dict and update only those fields

---

## Validation Strategy for Updates

When updating transactions, we need to validate:

### 1. **Existence Check**
```python
# Does this transaction exist?
transaction = db.query(Transaction).filter_by(id=transaction_id).first()
if not transaction:
    raise HTTPException(404, "Transaction not found")
```

### 2. **Ownership Check**
```python
# Does this transaction belong to the user?
if transaction.user_id != current_user_id:
    raise HTTPException(403, "Not your transaction")
```

### 3. **Business Rules Validation**

**XOR Constraint:** Transaction must have account OR credit card (not both, not neither)

```python
# If updating account_id or credit_card_id, ensure XOR constraint
if 'account_id' in update_data or 'credit_card_id' in update_data:
    # After update, must have exactly one
    new_account_id = update_data.get('account_id', transaction.account_id)
    new_credit_card_id = update_data.get('credit_card_id', transaction.credit_card_id)

    if not (bool(new_account_id) ^ bool(new_credit_card_id)):
        raise ValueError("Must have account OR credit card, not both")
```

**Account/Card Ownership:** If changing account/card, user must own the new one

```python
if 'account_id' in update_data:
    account = db.query(Account).filter_by(
        id=update_data['account_id'],
        user_id=current_user_id
    ).first()

    if not account:
        raise HTTPException(404, "Account not found or not accessible")
```

### 4. **Data Type Validation**

Pydantic handles this automatically:

```python
class TransactionUpdate(BaseModel):
    amount: Optional[Decimal] = None  # ← Pydantic ensures valid decimal
    date: Optional[datetime] = None   # ← Pydantic ensures valid datetime
```

If user sends invalid data:
```json
{
  "amount": "not a number"
}
```

Pydantic returns **422 Unprocessable Entity** with clear error message.

---

## Update Patterns in SQLAlchemy

### Pattern 1: Attribute Assignment (Simple)

```python
# Get the transaction
transaction = db.query(Transaction).filter_by(id=transaction_id).first()

# Update fields one by one
if 'description' in update_data:
    transaction.description = update_data['description']

if 'amount' in update_data:
    transaction.amount = update_data['amount']

# Commit
db.commit()
db.refresh(transaction)
```

**Pros:**
- ✅ Explicit - clear what's being updated
- ✅ Easy to debug
- ✅ Can add custom logic per field

**Cons:**
- ❌ Verbose for many fields
- ❌ Easy to forget a field

---

### Pattern 2: Loop Through Dict (DRY)

```python
# Get the transaction
transaction = db.query(Transaction).filter_by(id=transaction_id).first()

# Update all provided fields
for key, value in update_data.items():
    setattr(transaction, key, value)

# Commit
db.commit()
db.refresh(transaction)
```

**Pros:**
- ✅ DRY (Don't Repeat Yourself)
- ✅ Handles any number of fields
- ✅ Less code

**Cons:**
- ❌ Less explicit
- ❌ Harder to add field-specific logic

---

### Pattern 3: Hybrid (Recommended)

```python
# Get the transaction
transaction = db.query(Transaction).filter_by(id=transaction_id).first()

# Validate special fields first
if 'account_id' in update_data:
    # Validate account ownership
    validate_account_ownership(update_data['account_id'], user_id)

if 'credit_card_id' in update_data:
    # Validate card ownership
    validate_card_ownership(update_data['credit_card_id'], user_id)

# Validate XOR constraint if needed
if 'account_id' in update_data or 'credit_card_id' in update_data:
    validate_xor_constraint(transaction, update_data)

# Apply all updates
for key, value in update_data.items():
    setattr(transaction, key, value)

# Commit
db.commit()
db.refresh(transaction)
```

**Pros:**
- ✅ DRY for simple fields
- ✅ Custom logic for complex fields
- ✅ Best of both worlds

---

## Side Effects of Updates

When you update a transaction, other things might need to change:

### 1. **Balance Points** (if amount or date changes)

```python
# Old transaction:
{
  "date": "2025-01-15",
  "amount": 100.00
}

# User updates amount:
{
  "amount": 150.00
}

# Balance timeline is now WRONG!
# All balance points after 2025-01-15 need recalculation
```

**Solution:** Recalculate balance timeline after update (covered in balance-points guide)

---

### 2. **Audit Trail** (who changed what, when)

For compliance/debugging, you might want to track changes:

```python
# Option 1: Audit table
class TransactionAudit(Base):
    id = Column(UUID, primary_key=True)
    transaction_id = Column(UUID)
    field_name = Column(String)
    old_value = Column(String)
    new_value = Column(String)
    changed_by = Column(UUID)
    changed_at = Column(DateTime)

# Option 2: Simple updated_at timestamp
class Transaction(Base):
    # ...
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
```

**We're using Option 2 for now** (simple, good enough for most cases).

---

### 3. **Related Records**

Currently, transactions are fairly independent. But in the future:

- Updating recurring transaction → Update all future instances?
- Updating transaction with attachments → Validate attachment compatibility?
- Updating paid status → Trigger notification?

**For now:** Keep it simple, just update the transaction itself.

---

## Error Handling Strategy

### Common Errors:

**1. Transaction Not Found (404)**
```python
if not transaction:
    raise HTTPException(status_code=404, detail="Transaction not found")
```

**2. Not Authorized (403)**
```python
if transaction.user_id != current_user_id:
    raise HTTPException(status_code=403, detail="Not your transaction")
```

**3. Validation Error (422)**
```python
# Pydantic handles automatically
class TransactionUpdate(BaseModel):
    amount: Optional[Decimal] = None  # Invalid amount → 422
```

**4. Business Rule Violation (400)**
```python
# XOR constraint violation
if not (bool(account_id) ^ bool(credit_card_id)):
    raise HTTPException(status_code=400, detail="Must have account OR credit card")
```

**5. Database Error (500)**
```python
try:
    db.commit()
except IntegrityError as e:
    db.rollback()
    raise HTTPException(status_code=500, detail="Database error")
```

---

## Security Considerations

### 1. **User Isolation**

```python
# ❌ BAD - Allows editing any transaction
transaction = db.query(Transaction).filter_by(id=transaction_id).first()

# ✅ GOOD - Only user's transactions
transaction = db.query(Transaction).filter_by(
    id=transaction_id,
    user_id=current_user_id
).first()
```

### 2. **Mass Assignment Prevention**

```python
# ❌ BAD - User could send extra fields
update_data = request_body  # User sends {"id": "different-id", "amount": 100}

# ✅ GOOD - Pydantic schema only allows specific fields
class TransactionUpdate(BaseModel):
    amount: Optional[Decimal] = None
    # id is NOT in schema → silently ignored
```

### 3. **Rate Limiting** (future consideration)

```python
# Prevent abuse: user updating same transaction 1000 times/minute
@router.patch("/transactions/{transaction_id}")
@limiter.limit("10/minute")  # Max 10 updates per minute
def update_transaction(...):
    ...
```

---

## Testing Strategy

When implementing updates, test these scenarios:

### Happy Path
- ✅ Update single field
- ✅ Update multiple fields
- ✅ Update all fields

### Edge Cases
- ✅ Update with no fields (empty object)
- ✅ Update non-existent transaction (404)
- ✅ Update someone else's transaction (403)

### Business Rules
- ✅ XOR constraint validation
- ✅ Account ownership validation
- ✅ Invalid amount (negative, zero)
- ✅ Invalid date (future date)

### Idempotency
- ✅ Update same field twice → same result
- ✅ Update to same value → no change

---

## Comparison: Create vs Update

| Aspect | Create (POST) | Update (PATCH) |
|--------|---------------|----------------|
| **Fields** | Required | Optional |
| **Validation** | All fields | Only changed fields |
| **ID** | Generated by backend | Provided in URL |
| **Idempotent?** | No (creates new each time) | Yes (same result if repeated) |
| **Error if not exists** | N/A | 404 Not Found |
| **Ownership check** | None (you create it) | Required (must own it) |

---

## Next Steps

Now that you understand the concepts, we'll implement:

1. **Schema Layer** - Define `TransactionUpdate` with optional fields
2. **Repository Layer** - SQL update query with user isolation
3. **Service Layer** - Business logic and validation
4. **Router Layer** - PATCH endpoint with proper error handling

**Ready to implement?** Let's build it step by step with detailed explanations!
