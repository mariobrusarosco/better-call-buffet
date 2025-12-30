# Plan: Subscription Payment Projections (v1)

## 🎯 Objective
Create a new API endpoint that projects all upcoming subscription payments within a given timeframe. This will provide users with a clear view of their future recurring expenses, enabling better cash flow management.

## 🏗️ Architecture

This feature is primarily a "read" operation and will be implemented within the existing `subscriptions` domain.

- **New Endpoint**: `GET /api/v1/subscriptions/upcoming-bills`
- **Service Logic**: A new method in `SubscriptionService` will calculate the projected payments.
- **Response Schema**: A new Pydantic schema will define the structure of a projected payment.

## 📅 Implementation Phases

### Phase 1: Core Logic & Schemas
- **Sub-phase 1.1: Define Schemas**: Create `UpcomingPaymentResponse` and `UpcomingPaymentsListResponse` Pydantic models in `app/domains/subscriptions/schemas.py`.
- **Sub-phase 1.2: Implement Service Logic**: Add a `get_upcoming_bills` method to `SubscriptionService`. This method will contain the core logic for calculating future due dates based on each subscription's billing cycle.

### Phase 2: API Integration
- **Sub-phase 2.1: Create Router Endpoint**: Add the new `GET /upcoming-bills` endpoint to `app/domains/subscriptions/router.py`.
- **Sub-phase 2.2: Add Query Parameters**: Enhance the endpoint to accept `start_date` and `end_date` query parameters to define the projection window.

### Phase 3: Testing & Refinement
- **Sub-phase 3.1: Add Unit Tests**: Create a test file (`tests/test_subscriptions.py`) to validate the projection logic, especially around edge cases like end-of-month and leap years.
- **Sub-phase 3.2: Refine & Document**: Add OpenAPI documentation (docstrings) to the new endpoint to make it clear for frontend developers.

---

