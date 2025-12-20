# Transaction Editing - API Design & Implementation

## Overview

This document defines the API design and implementation plan for editing transactions in the Better Call Buffet application.

**Feature:** Allow users to update their existing transactions
**Method:** PATCH (partial updates)
**Endpoint:** `PATCH /api/v1/transactions/{transaction_id}`

---

## API Specification

### Endpoint

```
PATCH /api/v1/transactions/{transaction_id}
```

### Request

**Path Parameters:**
- `transaction_id` (UUID, required) - ID of transaction to update

**Headers:**
- `Authorization: Bearer <token>` - JWT authentication token

**Body:** (all fields optional)
```json
{
  "date": "2025-01-15T10:30:00Z",
  "amount": 150.00,
  "description": "Updated description",
  "category": "Food",
  "movement_type": "expense",
  "is_paid": true,
  "account_id": "abc-123-...",
  "credit_card_id": null
}
```

**Field Constraints:**
- Only include fields you want to update
- All fields are optional
- Must maintain XOR constraint (account_id XOR credit_card_id)
- Must maintain user ownership (can't move to another user's account)

---

### Response

**Success (200 OK):**
```json
{
  "id": "abc-123-...",
  "date": "2025-01-15T10:30:00Z",
  "amount": 150.00,
  "description": "Updated description",
  "category": "Food",
  "movement_type": "expense",
  "is_paid": true,
  "account_id": "abc-123-...",
  "credit_card_id": null,
  "user_id": "user-123-...",
  "created_at": "2025-01-10T08:00:00Z",
  "updated_at": "2025-01-19T14:22:00Z"
}
```

**Errors:**

| Status | Error | When |
|--------|-------|------|
| 404 | Transaction not found | Transaction doesn't exist or user doesn't own it |
| 403 | Not authorized | Trying to update another user's transaction |
| 400 | XOR constraint violation | Both account_id and credit_card_id provided/null |
| 400 | Invalid account/card | Account/card doesn't exist or user doesn't own it |
| 422 | Validation error | Invalid data type (e.g., amount not a number) |

---

## Implementation Layers

### Layer 1: Schema (Pydantic)

**File:** `app/domains/transactions/schemas.py`

**New Schema:**
```python
class TransactionUpdate(BaseModel):
    """
    Schema for updating an existing transaction (PATCH).

    All fields are optional - only include fields you want to update.
    """
    date: Optional[datetime] = None
    amount: Optional[Decimal] = None
    description: Optional[str] = None
    category: Optional[str] = None
    movement_type: Optional[str] = None
    is_paid: Optional[bool] = None
    account_id: Optional[UUID] = None
    credit_card_id: Optional[UUID] = None

    @field_validator('movement_type')
    @classmethod
    def validate_movement_type(cls, v):
        if v is not None and v not in ['income', 'expense']:
            raise ValueError('movement_type must be "income" or "expense"')
        return v

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        if v is not None and v <= 0:
            raise ValueError('amount must be greater than 0')
        return v
```

**Key Points:**
- All fields `Optional` with `= None` default
- Validators only run if field is provided
- Use `exclude_unset=True` when converting to dict

---

### Layer 2: Repository (Database)

**File:** `app/domains/transactions/repository.py`

**New Method:**
```python
def update_transaction(
    self,
    transaction_id: UUID,
    user_id: UUID,
    update_data: Dict[str, Any]
) -> Optional[Transaction]:
    """
    Update a transaction with only the fields in update_data.

    Args:
        transaction_id: ID of transaction to update
        user_id: ID of user (for ownership check)
        update_data: Dict of fields to update (from exclude_unset)

    Returns:
        Updated Transaction or None if not found

    Security:
        - Only updates transactions owned by user_id
        - Prevents unauthorized access
    """
    # Find transaction with user ownership check
    transaction = self.db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == user_id
    ).first()

    if not transaction:
        return None

    # Update only provided fields
    for key, value in update_data.items():
        setattr(transaction, key, value)

    # Update timestamp
    transaction.updated_at = datetime.utcnow()

    # Commit
    self.db.commit()
    self.db.refresh(transaction)

    return transaction
```

**Why user_id in query?**
- Security: Ensures user can only update their own transactions
- Simpler than separate ownership check
- Single database query (faster)

---

### Layer 3: Service (Business Logic)

**File:** `app/domains/transactions/service.py`

**New Method:**
```python
def update_transaction(
    self,
    transaction_id: UUID,
    user_id: UUID,
    update_schema: TransactionUpdate
) -> Transaction:
    """
    Update a transaction with business logic validation.

    Validates:
    - Transaction exists and user owns it
    - XOR constraint (account XOR credit card)
    - Account/card ownership (if changing)

    Args:
        transaction_id: ID of transaction to update
        user_id: Current user ID
        update_schema: Pydantic schema with fields to update

    Returns:
        Updated transaction

    Raises:
        HTTPException: If validation fails
    """
    # Convert to dict with only provided fields
    update_data = update_schema.model_dump(exclude_unset=True)

    # If no fields to update, return early
    if not update_data:
        # Just fetch and return existing transaction
        transaction = self.repository.get_transaction_by_id(transaction_id, user_id)
        if not transaction:
            raise HTTPException(404, "Transaction not found")
        return transaction

    # Validate account ownership if changing account
    if 'account_id' in update_data and update_data['account_id'] is not None:
        account = self.account_repository.get_account_by_id(
            update_data['account_id'],
            user_id
        )
        if not account:
            raise HTTPException(404, "Account not found or not accessible")

    # Validate credit card ownership if changing card
    if 'credit_card_id' in update_data and update_data['credit_card_id'] is not None:
        card = self.credit_card_repository.get_credit_card_by_id(
            update_data['credit_card_id'],
            user_id
        )
        if not card:
            raise HTTPException(404, "Credit card not found or not accessible")

    # Validate XOR constraint if changing account or card
    if 'account_id' in update_data or 'credit_card_id' in update_data:
        # Get current transaction to check final state
        current = self.repository.get_transaction_by_id(transaction_id, user_id)
        if not current:
            raise HTTPException(404, "Transaction not found")

        # Determine final values after update
        final_account_id = update_data.get('account_id', current.account_id)
        final_credit_card_id = update_data.get('credit_card_id', current.credit_card_id)

        # XOR check
        if not (bool(final_account_id) ^ bool(final_credit_card_id)):
            raise HTTPException(
                400,
                "Transaction must have either account_id or credit_card_id, not both"
            )

    # Perform update
    updated_transaction = self.repository.update_transaction(
        transaction_id,
        user_id,
        update_data
    )

    if not updated_transaction:
        raise HTTPException(404, "Transaction not found")

    return updated_transaction
```

**Business Logic Flow:**
1. Convert schema to dict (only provided fields)
2. Validate account ownership (if changing)
3. Validate card ownership (if changing)
4. Validate XOR constraint (if changing account/card)
5. Call repository to update
6. Return updated transaction

---

### Layer 4: Router (API Endpoint)

**File:** `app/domains/transactions/router.py`

**New Endpoint:**
```python
@router.patch("/{transaction_id}", response_model=TransactionResponse)
def update_transaction_endpoint(
    transaction_id: UUID,
    update_data: TransactionUpdate,
    db: Session = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    ✏️ Update an existing transaction (PATCH - partial update)

    Update one or more fields of an existing transaction.
    Only include the fields you want to change in the request body.

    Benefits:
    - ✅ Update only specific fields (flexible)
    - ✅ User ownership validation
    - ✅ XOR constraint validation
    - ✅ Account/card ownership validation

    Use Cases:
    - Fix incorrect transaction amount
    - Update transaction description
    - Change transaction category
    - Mark transaction as paid/unpaid
    - Move transaction to different account/card

    Request Body Examples:

    1. Update description only:
    {
        "description": "Groceries from Whole Foods"
    }

    2. Update amount and category:
    {
        "amount": 150.00,
        "category": "Food"
    }

    3. Move to different account:
    {
        "account_id": "new-account-id",
        "credit_card_id": null
    }

    Validation:
    - Transaction must exist and belong to user
    - If changing account/card, user must own the new account/card
    - Must maintain XOR constraint (account XOR credit card)
    - Amount must be positive
    - Movement type must be "income" or "expense"
    """
    service = TransactionService(db)
    return service.update_transaction(transaction_id, user_id, update_data)
```

**Key Points:**
- Path parameter: `transaction_id`
- Body: `TransactionUpdate` (all fields optional)
- Dependencies: database session + current user
- Response: Full `TransactionResponse` (updated transaction)

---

## Validation Matrix

| Update | Validations Required |
|--------|---------------------|
| `description` only | ✅ Transaction exists & owned by user |
| `amount` | ✅ Exists & owned<br>✅ Amount > 0 |
| `account_id` | ✅ Exists & owned<br>✅ Account exists & owned by user<br>✅ XOR constraint |
| `credit_card_id` | ✅ Exists & owned<br>✅ Card exists & owned by user<br>✅ XOR constraint |
| `movement_type` | ✅ Exists & owned<br>✅ Value in ["income", "expense"] |
| Empty `{}` | ✅ Exists & owned<br>Return unchanged |

---

## Error Scenarios & Handling

### Scenario 1: Transaction Not Found

**Request:**
```http
PATCH /transactions/non-existent-id
```

**Response:** 404
```json
{
  "detail": "Transaction not found"
}
```

---

### Scenario 2: Not User's Transaction

**Request:** (trying to update another user's transaction)
```http
PATCH /transactions/someone-elses-transaction
```

**Response:** 404 (same as not found for security)
```json
{
  "detail": "Transaction not found"
}
```

**Why 404 instead of 403?**
- Don't reveal existence of other users' transactions
- Security through obscurity

---

### Scenario 3: XOR Constraint Violation

**Request:**
```json
{
  "account_id": "abc-123",
  "credit_card_id": "xyz-789"
}
```

**Response:** 400
```json
{
  "detail": "Transaction must have either account_id or credit_card_id, not both"
}
```

---

### Scenario 4: Invalid Amount

**Request:**
```json
{
  "amount": -50.00
}
```

**Response:** 422 (Pydantic validation)
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "amount"],
      "msg": "amount must be greater than 0"
    }
  ]
}
```

---

### Scenario 5: Account Not Found/Not Owned

**Request:**
```json
{
  "account_id": "someone-elses-account"
}
```

**Response:** 404
```json
{
  "detail": "Account not found or not accessible"
}
```

---

## Side Effects & Considerations

### 1. Balance Timeline Impact

**If amount or date changes**, balance points need recalculation:

```python
# Future consideration - not implementing now
if 'amount' in update_data or 'date' in update_data:
    # Recalculate balance timeline for affected account
    self.balance_service.recalculate_timeline(account_id, from_date=old_date)
```

**For now:** Accept that balance timeline is calculated on-demand, so it will reflect updates automatically on next request.

---

### 2. Audit Trail

**Current:** We have `updated_at` timestamp

**Future consideration:**
- Track what changed (old value → new value)
- Track who changed it (user_id)
- Store in separate audit table

**For now:** `updated_at` timestamp is sufficient.

---

### 3. Bulk Updates

**Not implementing now**, but future consideration:

```python
# Future: Update multiple transactions
PATCH /transactions/bulk
{
  "updates": [
    {"id": "abc-123", "description": "Updated 1"},
    {"id": "xyz-789", "description": "Updated 2"}
  ]
}
```

**For now:** Single transaction updates only.

---

## Testing Plan

### Unit Tests (Service Layer)

```python
def test_update_transaction_description():
    """Test updating just the description"""
    # Arrange
    transaction = create_test_transaction()
    update = TransactionUpdate(description="New description")

    # Act
    result = service.update_transaction(transaction.id, user_id, update)

    # Assert
    assert result.description == "New description"
    assert result.amount == transaction.amount  # Unchanged

def test_update_transaction_not_found():
    """Test updating non-existent transaction"""
    update = TransactionUpdate(description="New")

    with pytest.raises(HTTPException) as exc:
        service.update_transaction(UUID(int=999), user_id, update)

    assert exc.value.status_code == 404

def test_update_xor_constraint_violation():
    """Test XOR constraint validation"""
    transaction = create_test_transaction(account_id=account_id)
    update = TransactionUpdate(
        account_id=account_id,
        credit_card_id=card_id  # Violates XOR
    )

    with pytest.raises(HTTPException) as exc:
        service.update_transaction(transaction.id, user_id, update)

    assert exc.value.status_code == 400

def test_update_someone_elses_transaction():
    """Test ownership validation"""
    transaction = create_test_transaction(user_id=other_user_id)
    update = TransactionUpdate(description="Hacked!")

    with pytest.raises(HTTPException) as exc:
        service.update_transaction(transaction.id, current_user_id, update)

    assert exc.value.status_code == 404
```

### Integration Tests (API Layer)

```python
def test_patch_transaction_success(client, auth_headers):
    """Test successful PATCH request"""
    # Create transaction
    transaction = create_test_transaction()

    # Update it
    response = client.patch(
        f"/api/v1/transactions/{transaction.id}",
        json={"description": "Updated"},
        headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json()["description"] == "Updated"

def test_patch_transaction_empty_body(client, auth_headers):
    """Test PATCH with no fields"""
    transaction = create_test_transaction()

    response = client.patch(
        f"/api/v1/transactions/{transaction.id}",
        json={},
        headers=auth_headers
    )

    # Should return unchanged transaction
    assert response.status_code == 200
    assert response.json()["id"] == str(transaction.id)
```

### Manual Tests (Postman)

1. ✅ Update description only
2. ✅ Update amount only
3. ✅ Update multiple fields
4. ✅ Update with empty body
5. ✅ Update non-existent transaction (404)
6. ✅ Update with XOR violation (400)
7. ✅ Update with invalid amount (422)
8. ✅ Move transaction to different account
9. ✅ Clear credit_card_id and set account_id

---

## Implementation Checklist

- [ ] Create `TransactionUpdate` schema in `schemas.py`
- [ ] Add validators for `movement_type` and `amount`
- [ ] Implement `update_transaction()` in repository
- [ ] Implement `update_transaction()` in service with validations
- [ ] Add PATCH endpoint in router
- [ ] Write unit tests for service layer
- [ ] Write integration tests for API layer
- [ ] Test manually with Postman
- [ ] Update API documentation
- [ ] Deploy and monitor

---

## Future Enhancements

1. **Bulk Updates** - Update multiple transactions in one request
2. **Audit Trail** - Track all changes with old/new values
3. **Balance Recalculation** - Auto-recalculate on amount/date change
4. **Validation Rules** - Custom business rules (e.g., max amount, date range)
5. **Optimistic Locking** - Prevent concurrent updates with version numbers
6. **Webhooks** - Notify external systems on transaction update

---

## References

- [Transaction Editing Concepts](../guides/transaction-editing-concepts.md) - Conceptual guide (PUT vs PATCH, patterns)
- [FastAPI PATCH Best Practices](https://fastapi.tiangolo.com/tutorial/body-updates/)
- [Pydantic Partial Models](https://docs.pydantic.dev/latest/concepts/models/#partial-models)
- [REST API Update Patterns](https://restfulapi.net/rest-put-vs-post/)
