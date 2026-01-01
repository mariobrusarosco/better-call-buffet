# Subscription Summary Enhancement Plan

## Goal
Enhance the `GET /api/subscriptions` endpoint to optionally return a comprehensive financial summary, including monthly burn rate, category breakdowns, and a 12-month forecast. This supports the "Financial Pulse" feature on the frontend.

## Phase 1: Schema Definitions
**Goal:** Define the data structures for the summary response.

### Tasks
- [x] **Task 1.1:** Define `CategoryBreakdownItem` and `MonthlyForecastItem` models in `schemas.py`.
- [x] **Task 1.2:** Define `SubscriptionSummary` model containing burn rate, projections, counts, and lists of breakdown items.
- [x] **Task 1.3:** Update `SubscriptionListMeta` to include an optional `summary` field.

## Phase 2: Service Logic Implementation
**Goal:** Implement the calculation logic for normalization and forecasting.

### Tasks
- [x] **Task 2.1:** Implement helper method `_normalize_to_monthly` in `SubscriptionService`.
- [x] **Task 2.2:** Implement `_calculate_monthly_forecast` to project costs over the next 12 months.
- [x] **Task 2.3:** Implement `get_subscription_summary` to aggregate all metrics (active count, burn rate, category breakdown, due next 30 days).
- [x] **Task 2.4:** Update `get_subscriptions` in `SubscriptionService` to conditionally fetch and attach the summary.

## Phase 3: Router & API Integration
**Goal:** Expose the functionality via the REST API.

### Tasks
- [x] **Task 3.1:** Update `get_subscriptions` in `router.py` to accept `include_summary: bool` query parameter.
- [x] **Task 3.2:** Pass the parameter to the service layer.

## Phase 4: Verification (DELAYED)
**Goal:** Verify the calculations and API response.

### Tasks
- [ ] **Task 4.1:** Run existing tests to ensure no regressions.
- [ ] **Task 4.2:** Manually verify the endpoint using a script or curl to check the summary calculations.

## Dependencies
- `app/domains/subscriptions/schemas.py`
- `app/domains/subscriptions/service.py`
- `app/domains/subscriptions/router.py`
- `app/domains/subscriptions/models.py` (BillingCycle enum)

## Expected Result
The `GET /api/subscriptions` response will include a `meta.summary` object when requested, providing the frontend with all necessary data for the subscription dashboard.
