# ADR 008: Subscriptions Domain & Reconciliation Strategy

## Status
Proposed

## Context
Users have recurring expenses (Netflix, Gym, AWS) that they want to track separately from standard transactions. They need to know:
1. When is the next payment due?
2. How much does this subscription cost me over time?
3. Have I paid this month's bill?

## Decision

### 1. Dedicated Domain
We will create a specific `subscriptions` domain rather than overloading Categories or Tags. Subscriptions have state (`next_due_date`, `active`) that simple categories do not possess.

### 2. Reconciliation over Automation
Instead of automatically creating "Ghost Transactions" when a bill is due, we will use a **Reconciliation Pattern**.
- **Why?** Real transactions eventually arrive via bank import/sync. Auto-creating transactions leads to duplicates (one fake, one real).
- **How?** Users "Mark as Paid" by selecting an *existing* transaction from their history.
- **Result:** The Transaction record gets tagged with `subscription_id`, effectively categorizing it and marking the cycle as complete.

### 3. Data Structure Changes
- **New Table**: `subscriptions`
- **Modified Table**: `transactions` (Add `subscription_id` column)

### 4. Renewal Logic
When a transaction is linked:
- The system should offer to automatically advance the `next_due_date` by the subscription's `billing_cycle`.

## Consequences
- **Positive**: Zero data duplication. 100% accuracy with bank statement.
- **Negative**: Requires manual user action to "link" payments (until we build AI auto-matching later).
