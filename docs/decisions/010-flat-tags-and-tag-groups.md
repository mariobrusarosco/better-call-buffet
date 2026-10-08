# ADR 010: Flat Tags and Tag Groups

**Status:** Accepted
**Date:** 2026-10-08
**Supersedes:** ADR 009 - the tag dimension and aggregation view parts (tags,
tag assignments and `EXISTS`-based matching stay as decided there)

## Context

ADR 009 introduced two structures on top of tags:

- **Tag dimensions**: folders of tags with a `single` / `multiple` selection mode,
  enforced on every transaction, subscription and installment plan.
- **Aggregation views**: named views holding a tree of nodes, each node carrying
  `include` / `exclude` tag conditions.

The frontend never shipped aggregation views and has removed dimensions. Users
think in a simpler model: tag freely, then save *combinations* of tags to see
where money goes ("Mother Health Expenses" = `health` + `mother`). Keeping
dimensions would keep rejecting tag combinations users legitimately want, and
keeping aggregation views next to a new groups feature would leave two
overlapping reporting systems, the situation ADR 009 itself rejected for
categories.

## Decision

1. **Tags are flat.** No dimensions, no selection modes. Any combination of up to
   `MAX_TAGS_PER_ENTITY` (20) tags is valid on any entity.
2. **Tag groups replace aggregation views.** A group is a name plus one or more
   tags, owned by a user, optionally nested under another group.
   - A group matches a transaction that has **all** of its *effective* tags: its
     own tags plus every ancestor's.
   - Only `include` semantics. No exclusions, no "any of" (both can be added
     later without changing the tables).
   - Nesting is capped at 8 levels; cycles are rejected.
   - Deleting a group deletes its subgroups (`ON DELETE CASCADE` on `parent_id`).
3. **Totals are computed on read** over all matching transactions in the
   Cashflow scope: the user's non-deleted, non-ignored transactions of one
   movement type, inside an inclusive date range (same bounds as the
   transactions list filters).
4. **Overlaps** are transactions shared by two or more groups that are not in an
   ancestor/descendant relationship. Among the groups a transaction matches, any
   group with a matching descendant is dropped (the child already implies it);
   two or more remaining groups means a real overlap.

## Consequences

### Positive

- One reporting concept that matches how users describe their money.
- Tagging never fails because of an organisational rule.
- Clicking a group can reuse the existing transaction filter
  (`tag_ids=<effective_tag_ids>&tag_match=all`).

### Negative

- Existing dimension and aggregation data is deleted by the migration
  (pre-production; acceptable). The downgrade recreates empty tables only.
- Group totals overlap by design and must never be summed into a grand total.
- The summary runs one aggregate query per group. Fine for tens of groups; see
  Evolution.

## Rejected alternatives

### Keep aggregation views and add groups beside them

Two systems that both answer "how much did I spend on X", with different rules.

### Implement groups on the aggregation tables

Views and exclude conditions would leak into a simpler model, and every group
would need a hidden wrapper view.

## Evolution

If the summary slows down with many groups, compute all groups in one statement
(one row per transaction with its tag array, matched in SQL or Python) or cache
per user and date range, invalidated by tag assignment changes.
