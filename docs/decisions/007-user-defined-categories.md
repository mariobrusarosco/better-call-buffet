# ADR 007: User-Defined Category System with 2-Level Hierarchy

**Status:** Accepted
**Date:** 2024-12-20
**Context:** Transaction categorization enhancement
**Supersedes:** Simple string-based category field

---

## Context and Problem Statement

Currently, transactions use a simple `category` string field where users can input any text. This approach has several limitations:

**Current Implementation:**
- Single `category` column (String, nullable) in `transactions` table
- No validation or structure
- No hierarchy support
- No user-specific category management
- Frontend sends freeform strings to backend

**Problems:**
1. **No Organization:** Users can't organize categories hierarchically (e.g., "Rent" → "Family", "Rent" → "Personal")
2. **No Consistency:** Typos create duplicate categories ("Food" vs "food" vs "Food ")
3. **No Management:** Users can't view, edit, or organize their categories
4. **Poor Analytics:** Hard to group and analyze spending by category/sub-category
5. **No Personalization:** All users forced to use same unstructured approach

**User Need:**
Based on UI mockups and requirements, users want:
- Hierarchical categorization (Category → Sub-Category)
- Personal category customization
- Consistent category management
- Better expense analysis and reporting

---

## Decision Drivers

1. **Production Data:** System has live users with existing transactions using string categories
2. **Migration Required:** Must preserve existing transaction categorizations
3. **User Experience:** Need intuitive 2-level hierarchy (not unlimited depth)
4. **Performance:** Category queries must remain fast
5. **Flexibility:** Users should create their own categories
6. **Simplicity:** Implementation should be maintainable and testable

---

## Considered Options

### Option 1: Fixed Two-Level Hierarchy (CHOSEN)

**Implementation:**
- Create `user_categories` table with self-referential `parent_id`
- `parent_id = NULL` → Top-level category
- `parent_id = UUID` → Sub-category
- Enforce max 2 levels in business logic
- Replace `transactions.category` (string) with `transactions.category_id` (UUID FK)

**Pros:**
✅ Simple, well-understood pattern
✅ Fast queries (single JOIN to get category + parent)
✅ Easy to validate (check parent depth before insert)
✅ Matches UI requirements exactly
✅ Can evolve to unlimited depth later if needed
✅ User-specific categories (personalization)

**Cons:**
⚠️ Limited to 2 levels (by design, not a real con for this use case)
⚠️ Requires data migration for existing transactions

### Option 2: Keep Simple String Field

**Implementation:**
- Keep current `category` string column
- Add validation/normalization at API layer
- No database changes

**Pros:**
✅ No migration needed
✅ Simple implementation

**Cons:**
❌ Doesn't solve the core problems
❌ No hierarchy support
❌ No category management
❌ Doesn't meet user requirements

**Decision:** Rejected - doesn't address user needs

### Option 3: Unlimited Depth Hierarchy (Adjacency List)

**Implementation:**
- Same as Option 1, but allow unlimited nesting
- Users can create Category → Sub → Sub-Sub → Sub-Sub-Sub...

**Pros:**
✅ Maximum flexibility

**Cons:**
❌ Over-engineering (YAGNI - You Ain't Gonna Need It)
❌ Complex recursive queries
❌ More complex UI (cascading dropdowns at N levels)
❌ Users don't need unlimited depth
❌ 2 levels is industry standard (Mint, YNAB, etc.)

**Decision:** Rejected - unnecessary complexity

### Option 4: Materialized Path

**Implementation:**
- Store full path as string: "Housing/Rent/Family"
- Fast reads, complex writes

**Pros:**
✅ Fast queries (no JOINs)

**Cons:**
❌ Path updates cascade to all children
❌ String length limits
❌ More complex maintenance
❌ Overkill for 2-level hierarchy

**Decision:** Rejected - unnecessary for our use case

---

## Decision Outcome

**Chosen Option:** Option 1 - Fixed Two-Level Hierarchy

### Rationale

1. **Meets Requirements:** Perfectly matches UI mockup and user needs
2. **Industry Standard:** Most finance apps use 2-level categorization (Mint, YNAB, Personal Capital)
3. **Simplicity:** Easy to implement, test, and maintain
4. **Performance:** Fast queries with single JOIN
5. **Evolvable:** Can remove depth limit later if users request it (schema stays the same)
6. **User Control:** Each user manages their own categories

### Implementation Summary

**Database Schema:**
```sql
CREATE TABLE user_categories (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) NOT NULL,
    name VARCHAR(100) NOT NULL,
    parent_id UUID REFERENCES user_categories(id) NULL,
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,

    CONSTRAINT uq_user_category_name UNIQUE (user_id, name, parent_id),
    INDEX idx_user_categories_user_parent (user_id, parent_id)
);

ALTER TABLE transactions ADD COLUMN category_id UUID REFERENCES user_categories(id);
```

**Hierarchy Rules:**
- Top-level: `parent_id = NULL`
- Sub-category: `parent_id = <top-level-category-id>`
- Max depth: 2 levels (enforced in service layer)

**API Changes:**
- `POST /api/v1/categories` - Create category/sub-category
- `GET /api/v1/categories` - Get user's category tree
- `PATCH /api/v1/categories/{id}` - Update category
- `DELETE /api/v1/categories/{id}` - Soft delete category

**Transaction Schema:**
- OLD: `{ "category": "Rent" }` (string)
- NEW: `{ "category_id": "uuid-here" }` (UUID reference)

---

## Consequences

### Positive

✅ **Better UX:** Users can organize expenses hierarchically
✅ **Personalization:** Each user creates categories that fit their life
✅ **Data Quality:** No more typos or duplicate categories
✅ **Better Analytics:** Can group by category AND sub-category
✅ **Scalability:** Database queries remain fast (indexed JOINs)
✅ **Maintainability:** Clear domain boundaries (categories domain)

### Negative

⚠️ **Migration Required:** Must migrate existing string categories to new structure
⚠️ **Breaking Change:** Frontend must update to use `category_id` instead of `category`
⚠️ **Deployment Coordination:** Backend and frontend must be updated together
⚠️ **Learning Curve:** Users need to understand category management UI

### Neutral

🔹 **Default Categories:** New users get 8 pre-populated categories (customizable)
🔹 **Backward Compatibility:** Temporary support for both old and new formats during migration
🔹 **Soft Delete:** Categories marked inactive rather than hard deleted

---

## Migration Strategy

### Phase 1: Add New Structure (Non-Breaking)
1. Create `user_categories` table
2. Add `category_id` column to `transactions` (nullable)
3. Keep old `category` column (for rollback safety)
4. Deploy backend with dual support

### Phase 2: Data Migration
1. Extract unique category strings per user
2. Create top-level `UserCategory` records for each unique string
3. Update transactions: `SET category_id = <mapped-uuid> WHERE category = <string>`
4. Verify: All transactions with category strings now have category_id

### Phase 3: Cleanup (Breaking Change)
1. Update frontend to use new API
2. Make `category_id` NOT NULL
3. Drop old `category` column
4. Remove backward compatibility code

**Detailed migration process:** See `docs/guides/category-migration-strategy.md`

---

## Validation Rules

1. **Unique Names:** User cannot have two categories with same name at same level
   - ✅ OK: "Personal" (top) + "Work" (top)
   - ❌ NOT OK: "Personal" (top) + "Personal" (top)
   - ✅ OK: "Personal" (top) + "Personal" (sub under "Rent") - different levels

2. **Max Depth:** Cannot create sub-category under another sub-category
   - ✅ OK: Category → Sub-Category
   - ❌ NOT OK: Category → Sub-Category → Sub-Sub-Category

3. **Ownership:** Users can only see/edit their own categories

4. **Deletion:** Cannot delete category if transactions reference it (soft delete instead)

5. **Transaction Constraint:** Every transaction must reference a valid, active category

---

## Default Categories

New users automatically receive these categories:

**Top-Level (8 categories):**
1. Housing (sub: Rent, Mortgage, Utilities, Maintenance)
2. Food (sub: Groceries, Restaurants, Delivery)
3. Transportation (sub: Gas, Public Transit, Car Payment)
4. Personal (sub: Clothing, Health, Entertainment)
5. Bills (sub: Phone, Internet, Subscriptions)
6. Shopping (sub: Electronics, Home, Gifts)
7. Education (sub: Courses, Books, Supplies)
8. Other (sub: Miscellaneous)

**Rationale:** Based on common personal finance categories from Mint, YNAB, and industry research.

Users can customize, rename, delete, or add to these as needed.

---

## References

- UI Mockup: Category/Sub-Category dropdowns
- Related Docs:
  - `docs/domains/user-categories.md` - Implementation specification
  - `docs/guides/category-migration-strategy.md` - Migration guide
- Similar Implementations:
  - Mint (Intuit): 2-level categories
  - YNAB: 2-level categories (Category Groups → Categories)
  - Personal Capital: 2-level categories

---

## Future Considerations

### Potential Enhancements (Not Implemented Now)

**1. Category Templates:**
- Users can share/import category structures
- "Use Mario's expense categories" feature

**2. AI-Powered Categorization:**
- Auto-suggest categories based on transaction description
- Learn from user's past categorizations

**3. Unlimited Depth:**
- If users request deeper hierarchies, remove depth validation
- Schema already supports it (just remove business logic check)

**4. Category Budgets:**
- Set spending limits per category
- Alert when approaching budget

**5. Category Analytics:**
- Spending trends by category over time
- Category-based reports and insights

### Decision to Revisit

If users consistently request:
- More than 2 levels of hierarchy
- Shared/public category templates
- Cross-user category standards

Then consider:
- Removing depth limit (enable unlimited hierarchy)
- Adding category marketplace/sharing
- Creating industry-standard category presets

---

## Notes

- This ADR supersedes the simple string-based `category` field
- Migration is **required** for production deployment
- Frontend changes are **required** (breaking change)
- Implementation timeline: ~2-3 days (backend + migration + testing)
- Users will need brief tutorial on new category management UI

---

**Decision By:** Development Team
**Approved By:** Product Owner
**Implementation Start:** 2024-12-20
