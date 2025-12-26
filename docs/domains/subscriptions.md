# Domain Guide: Subscriptions & Vendors

## Core Concept
We separate **Who** (Vendor) from **What** (Subscription) to allow clean grouping and analysis.

## Data Model

### 1. Vendor (`app/domains/vendors`)
Represents a merchant or payee.
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | PK |
| `user_id` | UUID | Owner |
| `name` | String | Unique per user (e.g. "Adobe") |
| `website`| String | Optional |

### 2. Subscription (`app/domains/subscriptions`)
Represents the contract/rule.
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | PK |
| `vendor_id`| UUID | FK to Vendors |
| `name` | String | e.g. "Creative Cloud" |
| `amount` | Decimal | Expected cost |
| `billing_cycle` | Enum | MONTHLY, YEARLY |
| `next_due_date` | Date | |

### 3. Transaction Integration
| Field | Type | Notes |
|-------|------|-------|
| `vendor_id` | UUID | FK to Vendors |
| `subscription_id` | UUID | FK to Subscriptions |

## Logic Flow

1. **User creates Vendor**: "Netflix"
2. **User creates Subscription**: "4K Plan", linked to "Netflix"
3. **User links Transaction**:
   - Selects transaction "NFLX.COM 123"
   - Links to "4K Plan"
   - System automatically sets Transaction's `vendor_id` to "Netflix"