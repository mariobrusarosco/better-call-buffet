# Balance Points Domain Refactoring Plan

## Overview
Refactor the balance_points domain to implement daily balance timeline tracking with historical transaction support and background recalculation capabilities.

## Architecture Summary

### Core Concept
- **Daily balance timeline**: Track account balance for each day
- **Historical transaction support**: Handle transactions added for past dates
- **Background recalculation**: Efficient processing of balance updates
- **Gap filling**: Clone previous day balance for days without transactions
- **2-year limit**: Only allow transactions within last 2 years

### Strategy
- **Range consolidation**: Recalculate from earliest dirty date to today
- **Smart merge**: Cancel/restart jobs only when new transaction is earlier
- **Lazy calculation**: Process on-demand when user requests timeline
- **Simple status**: Show "updating..." with refresh button for user control

## Phase 1: Database Foundation

### Task 1.1: Model Design & Migration
- [x] Update BalancePoint model with final schema
- [x] Create database migration for new structure
- [x] Add proper constraints and indexes
- [x] Test migration on development database

**Schema Design:**
```python
class BalancePoint(Base):
    __tablename__ = "balance_points"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    balance = Column(DECIMAL(15, 2), nullable=False)
    
    # Status tracking
    timeline_status = Column(String, default="current", nullable=False)  # current|updating|failed
    
    # Gap filling
    has_transactions = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Constraints & Indexes:**
- UniqueConstraint("account_id", "date") - One balance point per account per day
- Index("ix_balance_points_account_date", "account_id", "date") - Primary queries
- Index("ix_balance_points_status", "timeline_status") - Status filtering
- CheckConstraint for valid statuses and balance precision

### Task 1.2: Validation & Business Rules
- [ ] Implement 2-year transaction limit validation
- [ ] Add balance precision validation
- [ ] Create account-date uniqueness enforcement
- [ ] Add status validation (current/updating/failed)

## Phase 2: Core Repository Layer

### Task 2.1: Basic CRUD Operations
- [ ] Implement create_balance_point method
- [ ] Implement get_timeline method with date ranges
- [ ] Implement update_balance method
- [ ] Implement bulk operations for efficiency

### Task 2.2: Status Management
- [ ] Implement mark_as_updating method
- [ ] Implement mark_as_current method
- [ ] Implement mark_as_failed method
- [ ] Implement get_updating_accounts method

### Task 2.3: Gap Filling Operations
- [ ] Implement clone_previous_balance method
- [ ] Implement fill_gaps_in_range method
- [ ] Implement has_balance_point_for_date check
- [ ] Add gap detection utilities

## Phase 3: Service Layer Logic

### Task 3.1: Timeline Calculation
- [ ] Implement calculate_balance_for_date method
- [ ] Implement recalculate_range method
- [ ] Implement initial_balance_setup method
- [ ] Add transaction aggregation logic

### Task 3.2: Background Job Management
- [ ] Implement queue_balance_recalculation method
- [ ] Implement smart_merge_logic for concurrent updates
- [ ] Implement job cancellation logic
- [ ] Add job status tracking

### Task 3.3: Historical Transaction Handling
- [ ] Implement handle_historical_transaction method
- [ ] Implement range_consolidation logic
- [ ] Implement earliest_dirty_date calculation
- [ ] Add transfer transaction support (both accounts)

## Phase 4: API Integration

### Task 4.1: Router Endpoints
- [ ] Implement GET /accounts/{id}/balance-timeline endpoint
- [ ] Implement GET /accounts/{id}/balance-status endpoint
- [ ] Add date range validation and parsing
- [ ] Implement proper error responses

### Task 4.2: Response Schemas
- [ ] Create BalanceTimelineResponse schema
- [ ] Create BalanceStatusResponse schema
- [ ] Create error response schemas
- [ ] Add status messaging for frontend

## Phase 5: Background Processing

### Task 5.1: Job Processing Logic
- [ ] Implement background job processor
- [ ] Add job queue integration
- [ ] Implement progress tracking
- [ ] Add error handling and recovery

### Task 5.2: Integration Testing
- [ ] Test single historical transaction scenarios
- [ ] Test bulk transaction scenarios
- [ ] Test concurrent transaction additions
- [ ] Test job cancellation and restart logic

## Phase 6: Documentation & Cleanup

### Task 6.1: API Documentation
- [ ] Update OpenAPI documentation
- [ ] Add usage examples
- [ ] Document status codes and error responses
- [ ] Create integration guide

### Task 6.2: Testing & Validation
- [ ] Run full test suite
- [ ] Test migration on staging environment
- [ ] Validate performance with large datasets
- [ ] Confirm 2-year limit enforcement

## Edge Cases & Business Rules

### Account Creation
- User provides initial balance
- Create first balance point with user's initial balance

### Account Deletion
- Soft delete approach
- CASCADE delete balance points when account is deleted

### Transfer Transactions
- Both source and destination accounts get marked for update
- Background job processes both accounts

### Failed Jobs
- Update status to "failed"
- Provide retry mechanism
- Log error details for debugging

### Concurrent Access
- No multiple users per account (accounts bound to unique user_id)
- Handle concurrent transaction additions with smart merge

### Data Integrity
- 2-year transaction limit (transactions older than 730 days rejected)
- Balance precision constraints
- Unique constraint on account_id + date

## Implementation Notes

### Gap Filling Strategy
- Clone previous day's balance for days without transactions
- Mark cloned days with `has_transactions = false`

### Batch Processing
- Maximum 2 years of data per account (730 days max)
- Process entire range in single job (range consolidation)

### User Experience
- Simple "updating..." status indicator
- User-controlled refresh button to check completion
- Transparent messaging about background operations

### Performance Considerations
- Indexes optimized for account + date range queries
- Lazy calculation only when user requests timeline
- Background processing to avoid blocking user interactions

---

**Implementation Order:** Complete each task and mark as checked before proceeding to the next. Tasks within a phase can be worked sequentially, but phases should be completed in order to ensure proper dependency management.