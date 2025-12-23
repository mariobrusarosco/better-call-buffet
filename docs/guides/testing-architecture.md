# Testing Architecture Guide

## Philosophy: Test the Right Thing at the Right Layer

Testing is **not about code coverage**. It's about **confidence** that your system works correctly.

**Core Principle:** Each layer of your application should have **focused tests** that validate its specific responsibilities.

```
┌─────────────────────────────────────────┐
│         Router (API Layer)              │  ← Integration tests
│  "Does the HTTP endpoint work?"         │     (Full request → response)
├─────────────────────────────────────────┤
│         Service (Business Logic)        │  ← Unit tests
│  "Are business rules correct?"          │     (Mock dependencies)
├─────────────────────────────────────────┤
│      Repository (Data Access)           │  ← Unit tests
│  "Do database queries work?"            │     (Real test DB)
├─────────────────────────────────────────┤
│         Schema (Validation)             │  ← Unit tests
│  "Does Pydantic validate correctly?"    │     (Instant, no DB)
└─────────────────────────────────────────┘
```

---

## Why Test Each Layer Separately?

### Analogy: Testing a Car

**Bad approach:** Only test by driving the entire car
- Slow (start engine, drive, test every time)
- Hard to debug (is it engine? transmission? brakes?)
- Can't test edge cases easily

**Good approach:** Test components separately
- ⚡ Fast: Test spark plug without starting engine
- 🎯 Focused: Know exactly what broke
- 🧪 Thorough: Test edge cases per component

### In Your Backend:

**Without layer testing:**
```python
# Only integration tests
def test_update_transaction():
    # Start entire app, authenticate, create transaction, update it
    # Problem: If this fails, where's the bug?
    # - Schema validation?
    # - Business logic?
    # - Database query?
    # - HTTP handling?
```

**With layer testing:**
```python
# Schema test (instant)
def test_negative_amount_rejected():
    with pytest.raises(ValidationError):
        TransactionUpdate(amount=-50.00)
    # ✅ Clear: Schema validation works

# Service test (fast)
def test_xor_constraint_enforced():
    service.update_transaction(
        account_id=UUID(...),
        credit_card_id=UUID(...)
    )
    # ✅ Clear: Business logic works

# Integration test (slower but comprehensive)
def test_full_update_flow():
    response = client.patch("/transactions/123", json={...})
    # ✅ Clear: Entire flow works
```

---

## Test Structure: Mirror Your Domain

```
tests/
├── conftest.py                    # 🔧 Shared fixtures (DB, auth, factories)
├── factories.py                   # 🏭 Test data builders (users, accounts, transactions)
│
├── unit/                          # ⚡ Fast, isolated tests
│   └── domains/
│       └── transactions/
│           ├── test_schemas.py        # Pydantic validation
│           ├── test_service.py        # Business logic
│           └── test_repository.py     # Database operations
│
└── integration/                   # 🔗 Full flow tests
    └── api/
        └── v1/
            └── test_transactions_update.py  # End-to-end API tests
```

**Why this structure?**
- ✅ Mirrors your app structure (`app/domains/transactions/`)
- ✅ Easy to find tests for a domain
- ✅ Clear separation: unit vs integration
- ✅ Scales as you add domains

---

## The Testing Pyramid

```
        /\
       /  \     Few Integration Tests (Slow)
      /____\    - Happy paths
     /      \   - Critical user flows
    /________\
   /__________\  Many Unit Tests (Fast)
                 - Business rules
                 - Edge cases
                 - Error scenarios
```

### Why This Shape?

**Foundation (Unit Tests):**
- ⚡ Run in milliseconds
- 🎯 Pinpoint failures instantly
- 🧪 Test every edge case cheaply
- 🔄 Run constantly during development

**Top (Integration Tests):**
- 🐌 Slower (start DB, auth, HTTP)
- 🌐 Test realistic scenarios
- 🔗 Catch integration issues
- ✅ Validate user-facing behavior

**Example from your manual tests:**

| Test Type | Speed | When to Use | Your Examples |
|-----------|-------|-------------|---------------|
| Schema Unit | ⚡⚡⚡ Instant | Validate Pydantic rules | Test 6 (negative amount), Test 7 (invalid type) |
| Service Unit | ⚡⚡ Fast | Validate business logic | Test 5 (empty update), Tests 8-9 (XOR), Tests 11-12 (ownership) |
| Repository Unit | ⚡ Medium | Validate DB queries | Test 10 (transaction not found) |
| Integration | 🐌 Slow | Validate full API flow | Tests 1-4 (happy paths) |

---

## Layer 1: Schema Tests (Pydantic Validation)

### What to Test:
- Field validators (`@field_validator`)
- Type coercion (string → UUID, string → datetime)
- Optional vs required fields
- Custom validation logic

### Example from Your Code:

**Schema with validators:**
```python
# app/domains/transactions/schemas.py
class TransactionUpdate(BaseModel):
    amount: Optional[float] = None
    movement_type: Optional[str] = None

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        if v is not None and v <= 0:
            raise ValueError('amount must be greater than 0')
        return v

    @field_validator('movement_type')
    @classmethod
    def validate_movement_type(cls, v):
        if v is not None and v not in ['income', 'expense']:
            raise ValueError('movement_type must be "income" or "expense"')
        return v
```

**Test (maps to Test 6, Test 7):**
```python
# tests/unit/domains/transactions/test_schemas.py
import pytest
from pydantic import ValidationError
from app.domains.transactions.schemas import TransactionUpdate

class TestTransactionUpdateSchema:
    """Test Pydantic validation rules for transaction updates"""

    def test_negative_amount_rejected(self):
        """Test 6: Verify negative amounts are rejected at schema level"""
        with pytest.raises(ValidationError) as exc_info:
            TransactionUpdate(amount=-50.00)

        # Verify error details
        errors = exc_info.value.errors()
        assert any('amount must be greater than 0' in str(e) for e in errors)

    def test_zero_amount_rejected(self):
        """Edge case: Zero amount should also be rejected"""
        with pytest.raises(ValidationError):
            TransactionUpdate(amount=0.00)

    def test_positive_amount_accepted(self):
        """Happy path: Positive amounts are valid"""
        schema = TransactionUpdate(amount=100.50)
        assert schema.amount == 100.50

    def test_invalid_movement_type_rejected(self):
        """Test 7: Verify invalid movement types are rejected"""
        with pytest.raises(ValidationError) as exc_info:
            TransactionUpdate(movement_type="invalid")

        errors = exc_info.value.errors()
        assert any('must be "income" or "expense"' in str(e) for e in errors)

    def test_valid_movement_types_accepted(self):
        """Happy path: Valid movement types work"""
        income = TransactionUpdate(movement_type="income")
        assert income.movement_type == "income"

        expense = TransactionUpdate(movement_type="expense")
        assert expense.movement_type == "expense"

    def test_optional_fields_omittable(self):
        """Verify all fields are optional (partial update support)"""
        # Empty update is valid at schema level
        # (Business logic will reject it, but schema allows it)
        schema = TransactionUpdate()
        assert schema.amount is None
        assert schema.movement_type is None
```

**Why These Tests Matter:**
- ✅ Catch invalid input before hitting database
- ✅ Run instantly (no DB, no dependencies)
- ✅ Document validation rules clearly
- ✅ Pydantic gives clear 422 errors to API clients

**What NOT to Test:**
- ❌ Don't test Pydantic's built-in features (type coercion, JSON parsing)
- ❌ Don't test basic Python (str, int, float behavior)
- ❌ Only test YOUR custom validators

---

## Layer 2: Service Tests (Business Logic)

### What to Test:
- Business rules (XOR constraints, ownership checks)
- Validation logic (account exists, user owns account)
- State transitions (paid → unpaid)
- Error cases (not found, not authorized)

### Example from Your Code:

**Service with business logic:**
```python
# app/domains/transactions/service.py (simplified)
class TransactionService:
    def update_transaction(self, transaction_id, user_id, update_data_schema):
        update_data = update_data_schema.model_dump(exclude_unset=True)

        # Business Rule 1: Empty update check
        if not update_data:
            raise HTTPException(400, "No data provided to update")

        # Business Rule 2: Account ownership
        if "account_id" in update_data:
            account = self.account_service.get_account_by_id(
                update_data["account_id"], user_id
            )
            if not account:
                raise HTTPException(404, "Account not found")

        # Business Rule 3: XOR constraint
        if "account_id" in update_data or "credit_card_id" in update_data:
            current = self.repository.get_by_id(transaction_id)
            new_account = update_data.get("account_id", current.account_id)
            new_card = update_data.get("credit_card_id", current.credit_card_id)

            if new_account and new_card:
                raise HTTPException(400, "Must have account OR card, not both")
            if not new_account and not new_card:
                raise HTTPException(400, "Must have account OR card")

        return self.repository.update_transaction(transaction_id, user_id, update_data)
```

**Test (maps to Tests 5, 8, 9, 11, 12):**
```python
# tests/unit/domains/transactions/test_service.py
import pytest
from unittest.mock import Mock, MagicMock
from uuid import uuid4
from fastapi import HTTPException
from app.domains.transactions.service import TransactionService
from app.domains.transactions.schemas import TransactionUpdate

class TestTransactionServiceUpdate:
    """Test business logic for transaction updates"""

    @pytest.fixture
    def service(self):
        """Create service with mocked dependencies"""
        mock_db = Mock()
        service = TransactionService(mock_db)

        # Mock dependencies
        service.repository = Mock()
        service.account_service = Mock()
        service.credit_card_service = Mock()

        return service

    def test_empty_update_rejected(self, service):
        """Test 5: Empty updates should be rejected"""
        transaction_id = uuid4()
        user_id = uuid4()
        update_data = TransactionUpdate()  # No fields set

        with pytest.raises(HTTPException) as exc_info:
            service.update_transaction(transaction_id, user_id, update_data)

        assert exc_info.value.status_code == 400
        assert "No data provided" in str(exc_info.value.detail)

    def test_xor_violation_both_account_and_card(self, service):
        """Test 8: Cannot have both account_id and credit_card_id"""
        transaction_id = uuid4()
        user_id = uuid4()
        account_id = uuid4()
        card_id = uuid4()

        # Mock existing transaction
        mock_transaction = Mock(account_id=None, credit_card_id=card_id)
        service.repository.get_by_id.return_value = mock_transaction

        # Try to set both
        update_data = TransactionUpdate(
            account_id=account_id,
            credit_card_id=card_id
        )

        with pytest.raises(HTTPException) as exc_info:
            service.update_transaction(transaction_id, user_id, update_data)

        assert exc_info.value.status_code == 400
        assert "not both" in str(exc_info.value.detail).lower()

    def test_xor_violation_neither_account_nor_card(self, service):
        """Test 9: Must have either account_id or credit_card_id"""
        transaction_id = uuid4()
        user_id = uuid4()

        # Mock existing transaction with account
        mock_transaction = Mock(account_id=uuid4(), credit_card_id=None)
        service.repository.get_by_id.return_value = mock_transaction

        # Try to remove account without adding card
        update_data = TransactionUpdate(account_id=None)

        with pytest.raises(HTTPException) as exc_info:
            service.update_transaction(transaction_id, user_id, update_data)

        assert exc_info.value.status_code == 400
        assert "must have either" in str(exc_info.value.detail).lower()

    def test_account_ownership_validated(self, service):
        """Test 11: User must own the new account"""
        transaction_id = uuid4()
        user_id = uuid4()
        account_id = uuid4()

        # Mock: account not found (user doesn't own it)
        service.account_service.get_account_by_id.return_value = None

        update_data = TransactionUpdate(account_id=account_id)

        with pytest.raises(HTTPException) as exc_info:
            service.update_transaction(transaction_id, user_id, update_data)

        assert exc_info.value.status_code == 404
        assert "Account not found" in str(exc_info.value.detail)

    def test_credit_card_ownership_validated(self, service):
        """Test 12: User must own the new credit card"""
        transaction_id = uuid4()
        user_id = uuid4()
        card_id = uuid4()

        # Mock: credit card not found (user doesn't own it)
        service.credit_card_service.get_user_unique_credit_card_with_filters.return_value = None

        update_data = TransactionUpdate(credit_card_id=card_id)

        with pytest.raises(HTTPException) as exc_info:
            service.update_transaction(transaction_id, user_id, update_data)

        assert exc_info.value.status_code == 404
        assert "Credit card not found" in str(exc_info.value.detail)

    def test_successful_update_with_valid_account(self, service):
        """Happy path: Update succeeds when account exists and is owned"""
        transaction_id = uuid4()
        user_id = uuid4()
        account_id = uuid4()

        # Mock: account exists and is owned
        mock_account = Mock(id=account_id, user_id=user_id)
        service.account_service.get_account_by_id.return_value = mock_account

        # Mock: transaction exists
        mock_transaction = Mock(
            id=transaction_id,
            account_id=None,
            credit_card_id=uuid4()
        )
        service.repository.get_by_id.return_value = mock_transaction

        # Mock: successful update
        updated_transaction = Mock()
        service.repository.update_transaction.return_value = updated_transaction

        update_data = TransactionUpdate(account_id=account_id, credit_card_id=None)

        result = service.update_transaction(transaction_id, user_id, update_data)

        assert result == updated_transaction
        service.repository.update_transaction.assert_called_once()
```

**Why These Tests Matter:**
- ✅ Validate business rules without HTTP overhead
- ✅ Mock dependencies (fast, no real DB/services)
- ✅ Test error cases exhaustively
- ✅ Document business logic clearly

**Pattern: Arrange-Act-Assert (AAA):**
```python
def test_example(self, service):
    # ARRANGE: Set up test data and mocks
    user_id = uuid4()
    mock_account = Mock()
    service.account_service.get_account_by_id.return_value = mock_account

    # ACT: Call the method under test
    result = service.update_transaction(...)

    # ASSERT: Verify the outcome
    assert result == expected_value
    service.repository.update_transaction.assert_called_once()
```

---

## Layer 3: Repository Tests (Database Operations)

### What to Test:
- Database queries return correct data
- Filters work correctly (user_id isolation)
- Updates persist correctly
- NULL handling, default values

### Example from Your Code:

**Repository with DB logic:**
```python
# app/domains/transactions/repository.py (simplified)
class TransactionRepository:
    def update_transaction(self, transaction_id, user_id, update_data):
        """Update transaction fields. Returns None if not found/not owned."""
        transaction = (
            self.db.query(Transaction)
            .filter(
                Transaction.id == transaction_id,
                Transaction.user_id == user_id  # User isolation!
            )
            .first()
        )

        if not transaction:
            return None

        for key, value in update_data.items():
            setattr(transaction, key, value)

        self.db.commit()
        self.db.refresh(transaction)
        return transaction
```

**Test (maps to Test 10):**
```python
# tests/unit/domains/transactions/test_repository.py
import pytest
from uuid import uuid4
from datetime import datetime
from app.domains.transactions.repository import TransactionRepository
from app.domains.transactions.models import Transaction

class TestTransactionRepository:
    """Test database operations for transactions"""

    @pytest.fixture
    def repository(self, db_session):
        """Create repository with test database session"""
        return TransactionRepository(db_session)

    @pytest.fixture
    def sample_user_id(self):
        """Reusable user ID for tests"""
        return uuid4()

    @pytest.fixture
    def sample_transaction(self, db_session, sample_user_id):
        """Create a test transaction in the database"""
        transaction = Transaction(
            id=uuid4(),
            user_id=sample_user_id,
            broker_id=uuid4(),
            account_id=uuid4(),
            amount=100.00,
            description="Test transaction",
            movement_type="expense",
            category="Food",
            is_paid=False,
            date=datetime.now(),
        )
        db_session.add(transaction)
        db_session.commit()
        db_session.refresh(transaction)
        return transaction

    def test_transaction_not_found_returns_none(self, repository, sample_user_id):
        """Test 10: Non-existent transaction returns None"""
        fake_id = uuid4()
        result = repository.update_transaction(
            fake_id,
            sample_user_id,
            {"description": "Updated"}
        )
        assert result is None

    def test_transaction_owned_by_different_user_returns_none(
        self, repository, sample_transaction
    ):
        """Test 10 variant: User can't update someone else's transaction"""
        different_user_id = uuid4()
        result = repository.update_transaction(
            sample_transaction.id,
            different_user_id,  # Wrong user!
            {"description": "Hacked"}
        )
        assert result is None

    def test_single_field_update_persists(
        self, repository, sample_transaction, sample_user_id
    ):
        """Test 1 (repository layer): Single field updates work"""
        new_description = "Updated: Groceries from Whole Foods"

        result = repository.update_transaction(
            sample_transaction.id,
            sample_user_id,
            {"description": new_description}
        )

        assert result is not None
        assert result.description == new_description
        # Other fields unchanged
        assert result.amount == 100.00
        assert result.category == "Food"

    def test_multiple_field_update_persists(
        self, repository, sample_transaction, sample_user_id
    ):
        """Test 2 (repository layer): Multiple field updates work"""
        updates = {
            "amount": 175.50,
            "category": "Groceries"
        }

        result = repository.update_transaction(
            sample_transaction.id,
            sample_user_id,
            updates
        )

        assert result.amount == 175.50
        assert result.category == "Groceries"
        # Unchanged field
        assert result.description == "Test transaction"

    def test_null_values_handled_correctly(
        self, repository, sample_transaction, sample_user_id
    ):
        """Test switching from account to credit card (NULL handling)"""
        card_id = uuid4()
        updates = {
            "account_id": None,
            "credit_card_id": card_id
        }

        result = repository.update_transaction(
            sample_transaction.id,
            sample_user_id,
            updates
        )

        assert result.account_id is None
        assert result.credit_card_id == card_id
```

**Why These Tests Matter:**
- ✅ Verify SQL queries work correctly
- ✅ Test user isolation (security!)
- ✅ Ensure data persists correctly
- ✅ Catch database-specific issues (NULLs, constraints)

**Key Pattern: Use Real Test Database**
```python
# These tests use a REAL PostgreSQL test database
# Benefits:
# - Catch SQL syntax errors
# - Test database constraints
# - Verify NULL handling
# - Test transactions/rollbacks
```

---

## Layer 4: Integration Tests (Full API Flow)

### What to Test:
- HTTP requests work end-to-end
- Authentication works
- Status codes are correct
- Response format matches schema
- Happy paths for critical user flows

### Example (maps to Tests 1-4):

```python
# tests/integration/api/v1/test_transactions_update.py
import pytest
from uuid import uuid4
from httpx import AsyncClient
from app.main import app

class TestTransactionUpdateAPI:
    """Test full API flow for transaction updates"""

    @pytest.fixture
    async def authenticated_client(self, test_user, auth_token):
        """HTTP client with authentication"""
        async with AsyncClient(
            app=app,
            base_url="http://test",
            headers={"Authorization": f"Bearer {auth_token}"}
        ) as client:
            yield client

    @pytest.fixture
    def sample_transaction(self, test_user, test_account):
        """Create a transaction for testing"""
        # Use factory or service to create transaction
        return create_transaction(
            user_id=test_user.id,
            account_id=test_account.id,
            amount=150.00,
            description="Groceries",
            category="Food"
        )

    async def test_update_single_field_description(
        self, authenticated_client, sample_transaction
    ):
        """Test 1: Update only description field"""
        response = await authenticated_client.patch(
            f"/api/v1/transactions/{sample_transaction.id}",
            json={"description": "Updated: Groceries from Whole Foods"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated: Groceries from Whole Foods"
        # Verify other fields unchanged
        assert data["amount"] == 150.00
        assert data["category"] == "Food"

    async def test_update_multiple_fields(
        self, authenticated_client, sample_transaction
    ):
        """Test 2: Update amount and category simultaneously"""
        response = await authenticated_client.patch(
            f"/api/v1/transactions/{sample_transaction.id}",
            json={
                "amount": 175.50,
                "category": "Groceries"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["amount"] == 175.50
        assert data["category"] == "Groceries"
        # Description unchanged from Test 1
        assert data["description"] == "Updated: Groceries from Whole Foods"

    async def test_update_payment_status(
        self, authenticated_client, sample_transaction
    ):
        """Test 3: Mark transaction as paid"""
        response = await authenticated_client.patch(
            f"/api/v1/transactions/{sample_transaction.id}",
            json={"is_paid": True}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_paid"] is True

    async def test_switch_from_account_to_credit_card(
        self, authenticated_client, sample_transaction, test_credit_card
    ):
        """Test 4: Move transaction from account to credit card"""
        response = await authenticated_client.patch(
            f"/api/v1/transactions/{sample_transaction.id}",
            json={
                "account_id": None,
                "credit_card_id": str(test_credit_card.id)
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["account_id"] is None
        assert data["credit_card_id"] == str(test_credit_card.id)

    async def test_empty_update_returns_400(
        self, authenticated_client, sample_transaction
    ):
        """Test 5: Empty update rejected"""
        response = await authenticated_client.patch(
            f"/api/v1/transactions/{sample_transaction.id}",
            json={}
        )

        assert response.status_code == 400
        assert "No data provided" in response.json()["detail"]

    async def test_negative_amount_returns_422(
        self, authenticated_client, sample_transaction
    ):
        """Test 6: Negative amount rejected"""
        response = await authenticated_client.patch(
            f"/api/v1/transactions/{sample_transaction.id}",
            json={"amount": -50.00}
        )

        assert response.status_code == 422
        # Pydantic validation error
        detail = response.json()["detail"]
        assert any("amount must be greater than 0" in str(e) for e in detail)

    async def test_nonexistent_transaction_returns_404(
        self, authenticated_client
    ):
        """Test 10: Transaction not found"""
        fake_id = uuid4()
        response = await authenticated_client.patch(
            f"/api/v1/transactions/{fake_id}",
            json={"description": "This should fail"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
```

**Why These Tests Matter:**
- ✅ Validate actual user experience
- ✅ Catch integration issues (auth, serialization)
- ✅ Verify HTTP contract (status codes, response format)
- ✅ Test realistic scenarios

**When to Use:**
- Critical user flows (login, create transaction, update transaction)
- Happy paths that must always work
- End-to-end validation of features

---

## Test Data: Factories Pattern

### Problem: Test Setup is Repetitive

```python
# ❌ BAD: Duplicate setup in every test
def test_update_transaction():
    user = User(id=uuid4(), email="test@example.com", ...)
    broker = Broker(id=uuid4(), user_id=user.id, ...)
    account = Account(id=uuid4(), user_id=user.id, broker_id=broker.id, ...)
    transaction = Transaction(id=uuid4(), user_id=user.id, account_id=account.id, ...)
    # Finally, test something!
```

### Solution: Factory Pattern

```python
# tests/factories.py
from factory import Factory, Faker, SubFactory
from factory.alchemy import SQLAlchemyModelFactory
from app.domains.users.models import User
from app.domains.transactions.models import Transaction

class UserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session = None  # Set in conftest

    id = Faker('uuid4')
    email = Faker('email')
    hashed_password = "hashed_password_here"

class BrokerFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Broker
        sqlalchemy_session = None

    id = Faker('uuid4')
    name = Faker('company')
    user = SubFactory(UserFactory)

class AccountFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Account
        sqlalchemy_session = None

    id = Faker('uuid4')
    name = Faker('word')
    user = SubFactory(UserFactory)
    broker = SubFactory(BrokerFactory)

class TransactionFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Transaction
        sqlalchemy_session = None

    id = Faker('uuid4')
    description = Faker('sentence')
    amount = Faker('pydecimal', left_digits=4, right_digits=2, positive=True)
    category = Faker('word')
    movement_type = 'expense'
    is_paid = False
    date = Faker('date_time_this_year')
    user = SubFactory(UserFactory)
    account = SubFactory(AccountFactory)
```

**Usage in Tests:**
```python
# ✅ GOOD: Clean, readable test setup
def test_update_transaction(db_session):
    # Create test data with one line
    transaction = TransactionFactory(amount=100.00)

    # Test!
    updated = service.update_transaction(
        transaction.id,
        transaction.user_id,
        {"amount": 150.00}
    )

    assert updated.amount == 150.00

# Override specific fields when needed
def test_paid_transaction():
    transaction = TransactionFactory(is_paid=True, amount=500.00)
    # ...
```

**Benefits:**
- ✅ DRY: Define once, use everywhere
- ✅ Realistic data (Faker generates valid emails, names, etc.)
- ✅ Relationships handled automatically (user → broker → account)
- ✅ Override fields when needed
- ✅ Tests are readable

---

## Test Configuration: conftest.py

```python
# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.connection_and_session import Base
from tests.factories import UserFactory, TransactionFactory

# Test database URL (separate from development!)
TEST_DATABASE_URL = "postgresql://test:test@localhost:5432/testdb"

@pytest.fixture(scope="session")
def engine():
    """Create test database engine (once per test session)"""
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)  # Create tables
    yield engine
    Base.metadata.drop_all(engine)  # Clean up after all tests

@pytest.fixture(scope="function")
def db_session(engine):
    """
    Create a fresh database session for each test.

    Each test gets a clean slate - changes are rolled back after test.
    """
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    # Configure factories to use this session
    UserFactory._meta.sqlalchemy_session = session
    TransactionFactory._meta.sqlalchemy_session = session

    yield session

    # Rollback everything after test
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def test_user(db_session):
    """Create a test user"""
    return UserFactory()

@pytest.fixture
def auth_token(test_user):
    """Generate JWT token for test user"""
    from app.core.security import create_access_token
    return create_access_token(data={"sub": str(test_user.id)})

@pytest.fixture
async def authenticated_client(auth_token):
    """HTTP client with authentication headers"""
    from httpx import AsyncClient
    from app.main import app

    async with AsyncClient(
        app=app,
        base_url="http://test",
        headers={"Authorization": f"Bearer {auth_token}"}
    ) as client:
        yield client
```

**Why This Matters:**
- ✅ Each test gets a fresh database (no test pollution)
- ✅ Tests run in transactions (fast rollback)
- ✅ Reusable fixtures (DRY)
- ✅ Isolated test database (safe)

---

## Running Tests

### Docker-Based Testing (Recommended)

```bash
# Run all tests
docker compose exec web poetry run pytest

# Run specific test file
docker compose exec web poetry run pytest tests/unit/domains/transactions/test_schemas.py

# Run specific test
docker compose exec web poetry run pytest tests/unit/domains/transactions/test_service.py::TestTransactionServiceUpdate::test_empty_update_rejected

# Run with verbose output
docker compose exec web poetry run pytest -v

# Run with coverage report
docker compose exec web poetry run pytest --cov=app --cov-report=html

# Run only unit tests (fast!)
docker compose exec web poetry run pytest tests/unit/

# Run only integration tests
docker compose exec web poetry run pytest tests/integration/
```

### Test Markers (Organize by Speed)

```python
# Mark slow tests
@pytest.mark.slow
def test_full_database_migration():
    ...

# Mark integration tests
@pytest.mark.integration
async def test_api_endpoint():
    ...
```

**Run specific groups:**
```bash
# Run only fast tests (CI/pre-commit)
docker compose exec web poetry run pytest -m "not slow"

# Run only integration tests
docker compose exec web poetry run pytest -m integration
```

---

## Best Practices

### 1. **Test Naming Convention**

```python
# Pattern: test_<what>_<expected_outcome>
def test_negative_amount_rejected():       # ✅ Clear
def test_update():                         # ❌ Vague
def test_xor_violation_both_ids_raises_400():  # ✅ Very clear
```

### 2. **One Assertion Per Test (Mostly)**

```python
# ✅ GOOD: Focused test
def test_amount_updated():
    result = update_transaction(amount=150.00)
    assert result.amount == 150.00

# ❌ BAD: Testing too much
def test_everything():
    result = update_transaction(amount=150.00, description="New")
    assert result.amount == 150.00
    assert result.description == "New"
    assert result.category == "Food"
    assert result.is_paid == False
    # If this fails, which assertion broke?
```

**Exception:** Related assertions are OK:
```python
def test_response_format():
    response = client.get("/transactions")
    assert response.status_code == 200  # Related to next assertion
    assert "data" in response.json()    # Response structure
    assert "meta" in response.json()    # Response structure
```

### 3. **Use Fixtures for Reusable Setup**

```python
# ✅ GOOD: Reusable fixture
@pytest.fixture
def sample_transaction():
    return TransactionFactory(amount=100.00)

def test_update_description(sample_transaction):
    ...

def test_update_amount(sample_transaction):
    ...

# ❌ BAD: Duplicate setup
def test_update_description():
    transaction = TransactionFactory(amount=100.00)
    ...

def test_update_amount():
    transaction = TransactionFactory(amount=100.00)
    ...
```

### 4. **Test the Interface, Not Implementation**

```python
# ✅ GOOD: Test behavior
def test_user_can_update_transaction():
    result = service.update_transaction(id, user_id, {"amount": 150})
    assert result.amount == 150

# ❌ BAD: Test internal details
def test_update_calls_repository():
    service.update_transaction(...)
    # Don't assert on internal method calls unless testing integration
    assert service.repository.update_transaction.called
```

### 5. **Use Parametrized Tests for Similar Cases**

```python
# ✅ GOOD: One test, multiple scenarios
@pytest.mark.parametrize("movement_type,expected_valid", [
    ("income", True),
    ("expense", True),
    ("invalid", False),
    ("transfer", False),
])
def test_movement_type_validation(movement_type, expected_valid):
    if expected_valid:
        schema = TransactionUpdate(movement_type=movement_type)
        assert schema.movement_type == movement_type
    else:
        with pytest.raises(ValidationError):
            TransactionUpdate(movement_type=movement_type)

# ❌ BAD: Repetitive tests
def test_income_valid():
    schema = TransactionUpdate(movement_type="income")
    assert schema.movement_type == "income"

def test_expense_valid():
    schema = TransactionUpdate(movement_type="expense")
    assert schema.movement_type == "expense"

def test_invalid_rejected():
    with pytest.raises(ValidationError):
        TransactionUpdate(movement_type="invalid")
```

---

## CI/CD Integration

### GitHub Actions Test Workflow

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: testdb
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install Poetry
        run: pip install poetry

      - name: Install dependencies
        run: poetry install

      - name: Run linting
        run: |
          poetry run black --check .
          poetry run isort --check .
          poetry run flake8

      - name: Run tests
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/testdb
        run: poetry run pytest --cov=app --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

**Benefits:**
- ✅ Tests run on every push/PR
- ✅ Separate test database in CI
- ✅ Code coverage tracking
- ✅ Blocks merge if tests fail

---

## Common Pitfalls & Solutions

### Pitfall 1: Tests Pass Locally, Fail in CI

**Cause:** Tests depend on local state (files, database data)

**Solution:** Use fixtures and factories, clean slate per test
```python
# ✅ GOOD: Create what you need
def test_something(db_session):
    user = UserFactory()
    transaction = TransactionFactory(user=user)
    # Test is isolated

# ❌ BAD: Assume data exists
def test_something(db_session):
    user = db_session.query(User).first()  # Might not exist in CI!
```

### Pitfall 2: Slow Test Suite

**Cause:** Too many integration tests, not enough unit tests

**Solution:** Follow test pyramid - mostly unit tests
```python
# Run unit tests frequently (seconds)
docker compose exec web poetry run pytest tests/unit/

# Run integration tests less often (minutes)
docker compose exec web poetry run pytest tests/integration/
```

### Pitfall 3: Flaky Tests (Pass Sometimes, Fail Sometimes)

**Cause:** Tests depend on timing, order, or shared state

**Solution:** Isolate tests, use fixtures, avoid sleeps
```python
# ✅ GOOD: Deterministic
def test_create_transaction():
    transaction = TransactionFactory(amount=100.00)
    assert transaction.amount == 100.00

# ❌ BAD: Non-deterministic
def test_async_operation():
    start_async_task()
    time.sleep(1)  # Might not be enough time!
    assert task_complete()
```

### Pitfall 4: Testing Framework Features

**Cause:** Testing Pydantic, SQLAlchemy, FastAPI instead of your code

**Solution:** Only test YOUR custom logic
```python
# ✅ GOOD: Test your validator
def test_amount_must_be_positive():
    with pytest.raises(ValidationError):
        TransactionUpdate(amount=-50)

# ❌ BAD: Test Pydantic's type coercion
def test_string_converted_to_float():
    schema = TransactionUpdate(amount="100.50")
    assert schema.amount == 100.50
    # Pydantic already does this - don't test it!
```

---

## Mapping Your Manual Tests to Automated Tests

| Manual Test | Test Type | Layer | Test File |
|-------------|-----------|-------|-----------|
| Test 1: Update description | Integration | Router | `test_transactions_update.py::test_update_single_field` |
| Test 2: Update amount + category | Integration | Router | `test_transactions_update.py::test_update_multiple_fields` |
| Test 3: Update is_paid | Integration | Router | `test_transactions_update.py::test_update_payment_status` |
| Test 4: Switch account to card | Integration | Router | `test_transactions_update.py::test_switch_account_to_card` |
| Test 5: Empty update (400) | Unit | Service | `test_service.py::test_empty_update_rejected` |
| Test 6: Negative amount (422) | Unit | Schema | `test_schemas.py::test_negative_amount_rejected` |
| Test 7: Invalid type (422) | Unit | Schema | `test_schemas.py::test_invalid_movement_type` |
| Test 8: XOR both (400) | Unit | Service | `test_service.py::test_xor_both_rejected` |
| Test 9: XOR neither (400) | Unit | Service | `test_service.py::test_xor_neither_rejected` |
| Test 10: Not found (404) | Unit | Repository | `test_repository.py::test_transaction_not_found` |
| Test 11: Account not owned (404) | Unit | Service | `test_service.py::test_account_ownership` |
| Test 12: Card not owned (404) | Unit | Service | `test_service.py::test_card_ownership` |

**Coverage:**
- 4 integration tests (happy paths)
- 8 unit tests (business rules, edge cases)
- Total: 12 automated tests covering all manual scenarios

---

## Next Steps

### Phase 1: Foundation (Start Here)
1. Set up test database configuration
2. Create `conftest.py` with fixtures
3. Build basic factories (`UserFactory`, `TransactionFactory`)
4. Write your first integration test (Test 1)

### Phase 2: Unit Tests (Build Confidence)
1. Schema validation tests (Tests 6-7)
2. Service business logic tests (Tests 5, 8-9, 11-12)
3. Repository database tests (Test 10)

### Phase 3: Integration Tests (Cover User Flows)
1. Happy path scenarios (Tests 1-4)
2. Error scenarios end-to-end

### Phase 4: Scale & Optimize
1. Add more domains (accounts, credit cards)
2. Set up CI/CD test running
3. Track code coverage
4. Add performance tests if needed

---

## Questions to Consider

Before implementing tests, think about:

1. **What's the risk if this breaks?**
   - High risk → Integration test
   - Medium risk → Unit test
   - Low risk → Maybe skip

2. **How often will this change?**
   - Frequently → More tests
   - Stable → Fewer tests

3. **What layer owns this logic?**
   - Schema validation → Schema test
   - Business rules → Service test
   - Database query → Repository test
   - HTTP contract → Integration test

4. **Can I test this faster at a lower layer?**
   - If yes → Write unit test instead of integration test

---

## Resources

**Internal Documentation:**
- `/docs/guides/transaction-editing-concepts.md` - PATCH vs PUT, update patterns
- `/docs/database-migration-workflow.md` - Database testing setup
- `CLAUDE.md` - Development commands, Docker usage

**External Resources:**
- [Pytest Documentation](https://docs.pytest.org/)
- [Factory Boy](https://factoryboy.readthedocs.io/) - Test data generation
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)

---

**Remember:** Tests are documentation that runs. Write tests that clearly show **what** your code does and **why** it matters.
