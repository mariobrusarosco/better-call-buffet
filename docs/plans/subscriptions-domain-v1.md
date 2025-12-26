# Plan: Subscriptions & Vendors Implementation (v2)

## 🎯 Objective
Enable users to track recurring subscriptions and reconcile them with transactions, backed by a robust **Vendor** management system to ensure data consistency.

## 🏗️ Architecture

### 1. New Domain: `app/domains/vendors/`
- **Purpose**: Single source of truth for merchants/payees.
- **Model**: `Vendor` (id, user_id, name, logo_url, website).
- **Behavior**: Strict consistency (no duplicates per user).

### 2. New Domain: `app/domains/subscriptions/`
- **Purpose**: Manage recurring rules.
- **Model**: `Subscription` (links to `Vendor`).

### 3. Integration: `Transactions`
- **Update**: Add `vendor_id` FK (replaces raw strings where possible).

## 📅 Implementation Phases

### Phase 1: Vendors Domain (The Foundation)
- [ ] Create `app/domains/vendors/models.py`.
- [ ] Create `VendorService` and `VendorRepository`.
- [ ] Create `VendorRouter` (CRUD Endpoints).
- [ ] **Deliverable**: User can create "Netflix" and "Amazon" as vendors.

### Phase 2: Database Schema (Subscriptions & Transactions)
- [ ] Define `BillingCycle` Enum.
- [ ] Create `Subscription` model (FK to `Vendor`).
- [ ] Update `Transaction` model (Add `subscription_id` FK, Add `vendor_id` FK).
- [ ] Generate and apply Alembic migration for ALL changes.

### Phase 3: Subscriptions Logic
- [ ] Implement `SubscriptionRepository` & `SubscriptionService`.
- [ ] Implement `SubscriptionRouter` (CRUD).

### Phase 4: Reconciliation Logic
- [ ] Implement `link_payment` (Link Transaction -> Subscription).
- [ ] Auto-assign `vendor_id` to Transaction when linked to Subscription.

## 🧪 Testing Strategy
- **Vendors**: Ensure user isolation (User A cannot see User B's vendors).
- **Integrity**: Deleting a Vendor should genericize Subscriptions (Set NULL) or warn.