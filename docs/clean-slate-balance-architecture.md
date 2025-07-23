# 🚀 Clean Slate Balance Architecture Plan

## 🎯 **Project Context**

**Critical Advantage**: This project is not live yet, so we can start fresh without legacy constraints! This allows us to build the **perfect** balance architecture from day one.

**Current State**: 
- Existing test data can be completely reset
- No backward compatibility requirements
- Can design optimal database schema
- No migration complexity

---

## 🏗️ **Core Architectural Principles**

### **1. Transaction-First Architecture**
```
Source of Truth: Transaction History
Derived Data: Account Balances (cached for performance)
Flow: Transaction → Calculate Impact → Update Balance → Commit
```

### **2. Automatic Balance Consistency**
```
✅ EVERY transaction creation = automatic balance update
✅ NO manual balance management needed
✅ Perfect consistency from day one
✅ Zero tolerance for discrepancies
```

### **3. Professional Financial Standards**
```
✅ Decimal precision for all monetary values
✅ Proper audit trail for all balance changes
✅ Atomic transactions (all-or-nothing updates)
✅ Comprehensive validation rules
```

---

## 💾 **Enhanced Database Schema Design**

### **🔄 Enhanced Transaction Model**
```python
class Transaction(Base):
    __tablename__ = "transactions"
    
    # Primary Key
    id = Column(UUID, primary_key=True, default=uuid4)
    
    # Core Transaction Data
    amount = Column(DECIMAL(15, 2), nullable=False)  # Use Decimal for precision
    description = Column(String, nullable=False)
    date = Column(DateTime, nullable=False)
    
    # Movement Classification
    movement_type = Column(String, nullable=False)  # "income" | "expense" | "transfer"
    category = Column(String, nullable=True)
    
    # NEW: Calculated Balance Impact
    balance_impact = Column(DECIMAL(15, 2), nullable=False)  # Pre-calculated for performance
    
    # Transaction Targets (XOR + Transfer support)
    account_id = Column(UUID, ForeignKey("accounts.id"), nullable=True)
    credit_card_id = Column(UUID, ForeignKey("credit_cards.id"), nullable=True)
    
    # NEW: Transfer Support
    from_account_id = Column(UUID, ForeignKey("accounts.id"), nullable=True)
    to_account_id = Column(UUID, ForeignKey("accounts.id"), nullable=True)
    
    # Payment Linking
    related_transaction_id = Column(UUID, ForeignKey("transactions.id"), nullable=True)
    
    # Metadata
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    is_paid = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('amount > 0', name='positive_amount'),
        CheckConstraint(
            '(account_id IS NOT NULL)::int + '
            '(credit_card_id IS NOT NULL)::int + '
            '(from_account_id IS NOT NULL AND to_account_id IS NOT NULL)::int = 1',
            name='single_transaction_target'
        ),
    )
```

### **💰 Enhanced Account Model**
```python
class Account(Base):
    __tablename__ = "accounts"
    
    # Existing fields...
    id = Column(UUID, primary_key=True, default=uuid4)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # "checking", "savings", "investment"
    currency = Column(String, default="BRL", nullable=False)
    
    # Enhanced Balance Management
    balance = Column(DECIMAL(15, 2), default=Decimal('0.00'), nullable=False)
    available_balance = Column(DECIMAL(15, 2), default=Decimal('0.00'), nullable=False)  # For holds/pending
    
    # NEW: Balance Tracking
    last_transaction_id = Column(UUID, ForeignKey("transactions.id"), nullable=True)
    balance_updated_at = Column(DateTime, default=datetime.utcnow)
    
    # Existing metadata...
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    broker_id = Column(UUID, ForeignKey("brokers.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### **💳 Enhanced Credit Card Model**
```python
class CreditCard(Base):
    __tablename__ = "credit_cards"
    
    # Existing fields...
    id = Column(UUID, primary_key=True, default=uuid4)
    name = Column(String, nullable=False)
    account_id = Column(UUID, ForeignKey("accounts.id"), nullable=False)  # Linked account
    
    # Enhanced Credit Management
    credit_limit = Column(DECIMAL(15, 2), nullable=True)
    current_balance = Column(DECIMAL(15, 2), default=Decimal('0.00'), nullable=False)  # Outstanding debt
    available_credit = Column(DECIMAL(15, 2), nullable=True)  # Calculated field
    
    # NEW: Balance Tracking (same as accounts)
    last_transaction_id = Column(UUID, ForeignKey("transactions.id"), nullable=True)
    balance_updated_at = Column(DateTime, default=datetime.utcnow)
    
    # Existing metadata...
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    broker_id = Column(UUID, ForeignKey("brokers.id"), nullable=False)
    due_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

---

## 🔄 **Transaction Flow Patterns**

### **1. Simple Account Transaction**
```python
# Deposit: +$500 to checking account
Transaction(
    account_id="uuid-checking-account",
    amount=Decimal('500.00'),
    movement_type="income",
    balance_impact=Decimal('500.00'),  # Increases account balance
    description="Salary deposit",
    category="salary"
)

# Result: Account balance increases by $500
```

### **2. Credit Card Transaction**
```python
# Purchase: $75 restaurant bill on credit card
Transaction(
    credit_card_id="uuid-credit-card",
    amount=Decimal('75.00'),
    movement_type="expense",
    balance_impact=Decimal('75.00'),  # Increases credit card debt
    description="Restaurant XYZ",
    category="dining"
)

# Result: Credit card balance (debt) increases by $75
# Note: Linked account balance unchanged
```

### **3. Account-to-Account Transfer**
```python
# Transfer: $200 from checking to savings
[
    Transaction(
        from_account_id="uuid-checking",
        to_account_id="uuid-savings",
        amount=Decimal('200.00'),
        movement_type="transfer",
        balance_impact=Decimal('-200.00'),  # Sender account
        description="Transfer to savings"
    ),
    Transaction(
        from_account_id="uuid-checking", 
        to_account_id="uuid-savings",
        amount=Decimal('200.00'),
        movement_type="transfer",
        balance_impact=Decimal('200.00'),   # Receiver account
        description="Transfer from checking",
        related_transaction_id="uuid-sender-transaction"
    )
]

# Result: Checking -$200, Savings +$200
```

### **4. Credit Card Payment**
```python
# Pay credit card from checking account
Transaction(
    account_id="uuid-checking",
    credit_card_id="uuid-credit-card",  # Links payment to card
    amount=Decimal('300.00'),
    movement_type="expense",
    balance_impact=Decimal('-300.00'),  # Reduces account balance
    description="Credit card payment",
    category="payment"
)

# Companion transaction on credit card side
Transaction(
    credit_card_id="uuid-credit-card",
    amount=Decimal('300.00'),
    movement_type="income",  # Payment reduces debt
    balance_impact=Decimal('-300.00'),  # Reduces credit card debt
    description="Payment received",
    related_transaction_id="uuid-account-payment"
)

# Result: Account -$300, Credit card debt -$300
```

---

## ⚙️ **Balance Calculation Engine**

### **Core Balance Update Logic**
```python
def update_balance_for_transaction(transaction: Transaction):
    """
    Update account or credit card balance based on transaction.
    This is the core balance consistency engine.
    """
    if transaction.account_id:
        # Update account balance
        account = get_account(transaction.account_id)
        account.balance += transaction.balance_impact
        account.last_transaction_id = transaction.id
        account.balance_updated_at = datetime.utcnow()
        
    elif transaction.credit_card_id:
        # Update credit card balance (debt)
        card = get_credit_card(transaction.credit_card_id)
        card.current_balance += transaction.balance_impact
        card.available_credit = card.credit_limit - card.current_balance
        card.last_transaction_id = transaction.id
        card.balance_updated_at = datetime.utcnow()
        
    elif transaction.from_account_id and transaction.to_account_id:
        # Handle transfer (two balance updates)
        update_account_balance(transaction.from_account_id, -transaction.amount)
        update_account_balance(transaction.to_account_id, +transaction.amount)
```

### **Balance Impact Calculation Rules**
```python
def calculate_balance_impact(transaction_data: dict) -> Decimal:
    """
    Pre-calculate the balance impact for consistent updates.
    """
    amount = Decimal(str(transaction_data['amount']))
    movement_type = transaction_data['movement_type']
    
    if transaction_data.get('account_id'):
        # Account transactions
        if movement_type == "income":
            return +amount  # Increases account balance
        elif movement_type == "expense":
            return -amount  # Decreases account balance
        elif movement_type == "transfer":
            # Handled separately for from/to accounts
            return amount if transaction_data.get('to_account_id') else -amount
            
    elif transaction_data.get('credit_card_id'):
        # Credit card transactions
        if movement_type == "expense":
            return +amount  # Increases debt (positive balance = debt)
        elif movement_type == "income":  # Payments
            return -amount  # Reduces debt
            
    raise ValueError(f"Cannot calculate balance impact for transaction: {transaction_data}")
```

---

## 🛡️ **Data Integrity & Validation**

### **Database Constraints**
```sql
-- Ensure positive amounts
ALTER TABLE transactions ADD CONSTRAINT positive_amount CHECK (amount > 0);

-- Ensure single transaction target (XOR logic)
ALTER TABLE transactions ADD CONSTRAINT single_target CHECK (
    (account_id IS NOT NULL)::int + 
    (credit_card_id IS NOT NULL)::int + 
    (from_account_id IS NOT NULL AND to_account_id IS NOT NULL)::int = 1
);

-- Prevent self-transfers
ALTER TABLE transactions ADD CONSTRAINT no_self_transfer CHECK (
    from_account_id IS NULL OR to_account_id IS NULL OR from_account_id != to_account_id
);

-- Ensure balance precision
ALTER TABLE accounts ADD CONSTRAINT balance_precision CHECK (
    balance = ROUND(balance, 2)
);
```

### **Application-Level Validation**
```python
class TransactionValidator:
    @staticmethod
    def validate_transaction(transaction_data: dict, user_id: UUID):
        # XOR validation
        targets = [
            transaction_data.get('account_id'),
            transaction_data.get('credit_card_id'),
            transaction_data.get('from_account_id') and transaction_data.get('to_account_id')
        ]
        if sum(bool(target) for target in targets) != 1:
            raise ValidationError("Transaction must have exactly one target")
        
        # Ownership validation
        if transaction_data.get('account_id'):
            validate_account_ownership(transaction_data['account_id'], user_id)
        
        # Sufficient funds validation (for expenses and transfers)
        if transaction_data['movement_type'] in ['expense', 'transfer']:
            validate_sufficient_funds(transaction_data, user_id)
        
        # Amount validation
        if Decimal(str(transaction_data['amount'])) <= 0:
            raise ValidationError("Amount must be positive")
```

---

## 🚀 **Implementation Phases**

### **Phase 1: Core Balance Engine (2-3 days)**
- [ ] Enhanced transaction model with `balance_impact`
- [ ] Automatic balance updates on transaction creation
- [ ] Basic validation rules (XOR, positive amounts)
- [ ] Single transaction creation with balance sync
- [ ] Balance calculation from transaction history

### **Phase 2: Advanced Transaction Types (2-3 days)**
- [ ] Account-to-account transfers
- [ ] Credit card payment linking
- [ ] Bulk transaction operations with balance updates
- [ ] Transfer validation (sufficient funds)

### **Phase 3: Professional Features (3-4 days)**
- [ ] Balance reconciliation endpoints
- [ ] Historical balance calculations
- [ ] Multi-currency support (if needed)
- [ ] Advanced reporting and analytics
- [ ] Performance optimization

### **Phase 4: Production Readiness (2-3 days)**
- [ ] Comprehensive test suite
- [ ] Error handling and rollback scenarios
- [ ] API documentation
- [ ] Performance benchmarking
- [ ] Deployment preparation

---

## 🎛️ **Configuration & Business Rules**

### **Balance Configuration**
```python
# app/core/balance_config.py
@dataclass
class BalanceConfig:
    # Precision and formatting
    DECIMAL_PLACES: int = 2
    DEFAULT_CURRENCY: str = "BRL"
    
    # Balance rules
    ALLOW_NEGATIVE_ACCOUNT_BALANCES: bool = False
    ALLOW_CREDIT_CARD_OVERLIMIT: bool = False
    
    # Transfer rules
    ENABLE_ACCOUNT_TRANSFERS: bool = True
    TRANSFER_FEE_PERCENTAGE: Decimal = Decimal('0.0')
    MAX_TRANSFER_AMOUNT: Optional[Decimal] = None
    
    # Credit card behavior
    CREDIT_CARDS_SEPARATE_FROM_ACCOUNTS: bool = True
    AUTO_PAY_CREDIT_CARDS: bool = False
    
    # Performance
    ENABLE_BALANCE_CACHING: bool = True
    CACHE_EXPIRY_SECONDS: int = 300
```

### **Movement Type Definitions**
```python
class MovementType:
    INCOME = "income"      # Money coming in
    EXPENSE = "expense"    # Money going out
    TRANSFER = "transfer"  # Money moving between accounts
    PAYMENT = "payment"    # Specific type of expense (credit card payments)
    ADJUSTMENT = "adjustment"  # Manual corrections
    
    # Future extensions
    REFUND = "refund"      # Expense reversals
    INTEREST = "interest"  # Earned interest
    FEE = "fee"           # Bank fees
```

---

## 🎯 **Key Architectural Decisions**

### **Decision 1: Credit Card Balance Philosophy**
**Chosen Approach**: **Separate Balances** (Professional Banking Model)
- ✅ Account balance = Account transactions only
- ✅ Credit card balance = Outstanding debt only
- ✅ Matches real banking behavior
- ✅ Clearer financial picture

### **Decision 2: Transaction-First Design**
**Chosen Approach**: **Transactions as Source of Truth**
- ✅ All balances derived from transaction history
- ✅ Cached balances for performance
- ✅ Perfect auditability
- ✅ Easy to add new balance types

### **Decision 3: Decimal Precision**
**Chosen Approach**: **Python Decimal + Database DECIMAL(15,2)**
- ✅ No floating-point errors
- ✅ Professional financial precision
- ✅ Consistent across application layers
- ✅ Database-level precision enforcement

### **Decision 4: Schema Migration Strategy**
**Chosen Approach**: **Fresh Start** (since no production data)
- ✅ Optimal database schema from day one
- ✅ No migration complexity
- ✅ Can use best practices without constraints
- ✅ Clean implementation

---

## ❓ **Open Questions for Discussion**

### **1. Transfer Requirements**
- Should we support transfers between different users' accounts?
- Do we need transfer fees or limits?
- Should transfers be instant or have pending states?

### **2. Credit Card Advanced Features**
- Do we need minimum payment calculations?
- Should we track interest charges?
- Do we need credit utilization reporting?

### **3. Multi-Currency Support**
- Single currency (BRL) sufficient for now?
- Need real-time exchange rates if multi-currency?
- How to handle currency conversion fees?

### **4. Performance Requirements**
- Expected transaction volume per day?
- Real-time balance updates required, or eventual consistency OK?
- Need to support high-frequency trading scenarios?

### **5. Reporting & Analytics**
- What kind of balance history reports needed?
- Need cash flow analysis features?
- Monthly/yearly balance summaries required?

---

## 📋 **Next Steps**

1. **Finalize open questions** (discuss with team)
2. **Create database migration scripts** (fresh schema)
3. **Implement Phase 1 core features**
4. **Add comprehensive test coverage**
5. **Create API documentation**
6. **Performance testing and optimization**

---

This clean-slate approach gives us the opportunity to build a **professional, scalable, and maintainable** balance management system that follows industry best practices while being perfectly suited to your application's needs!