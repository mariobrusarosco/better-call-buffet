# ADR 009: Tag-Based Classification and Aggregation Trees

**Status:** Accepted
**Date:** 2026-10-08
**Supersedes:** ADR 007 - User-Defined Category System with 2-Level Hierarchy

## Context

A transaction can describe several independent facts. For example, an expense can
be about `Health`, benefit `Mother`, be for `Medication`, and be `Reimbursable`.
A single category path forces those facts into one ordering and duplicates concepts
when users want a different view of the same data.

Users also need reusable, nested reporting structures. The same transaction should
be visible through views such as:

```text
Health Expenses [Health]
├── Mother [Mother]
│   ├── Medication [Medication]
│   └── Appointments [Appointment]
└── Myself [Myself]
```

Each child adds a predicate to the predicates inherited from its ancestors.

## Decision drivers

- Classifications must compose across independent dimensions.
- Users need more than two reporting levels.
- A transaction must be reusable in several reporting views without duplication.
- Financial totals must not be multiplied by SQL joins.
- The project is pre-production, so a clean break is preferable to maintaining two
  competing classification systems.
- PostgreSQL remains the source of truth. Expected personal-finance scale is below
  100,000 transactions per user and normally below ten tags per transaction.

## Decision

Replace user categories with four concepts:

1. **Tag dimensions** organize tags and declare whether a transaction may select
   one or many tags from the dimension.
2. **Tags** are flat, atomic facts owned by one user.
3. **Tag assignments** form many-to-many relationships between tags and
   transactions, subscription templates, and installment-plan templates.
4. **Aggregation views** contain nested nodes. Each node contributes included or
   excluded tag conditions. Its effective predicate is the conjunction of its own
   conditions and every ancestor's conditions.

The initial query language supports:

- `include`: the transaction must have the tag.
- `exclude`: the transaction must not have the tag.
- Multiple conditions and inherited conditions are combined with `AND`.

`ANY` groups are intentionally deferred. They can be added later without changing
the core tables.

## Accounting semantics

- A transaction is counted at most once inside a single aggregation node.
- Parent totals are calculated directly from the parent's effective predicate; they
  are not calculated by summing children.
- Sibling nodes may overlap when their conditions use multi-select or ungrouped
  tags. Their totals therefore are not necessarily additive.
- A single-select dimension prevents a transaction from receiving more than one
  active tag from that dimension. Siblings built from one such dimension can form
  an additive breakdown, with unmatched transactions shown separately by clients.

## Limits

- Maximum 20 tags per transaction, subscription, or installment plan.
- Maximum aggregation depth of 8.
- Maximum 100 nodes per aggregation view.
- Tag and dimension deletion is soft so historical assignments remain readable.
- Aggregation definitions are hard-deleted because they are presentation rules,
  not financial records.

## Data model

```text
tag_dimensions 1 ─── * tags
transactions   * ─── * tags (transaction_tags)
subscriptions  * ─── * tags (subscription_tags)
installment_plans * ─ * tags (installment_plan_tags)

aggregation_views 1 ─── * aggregation_nodes
aggregation_nodes 1 ─── * aggregation_node_conditions
aggregation_nodes 1 ─── * aggregation_nodes (parent/children)
```

Tag names and dimension names are normalized with Unicode `casefold()` and are
unique per user. Ownership is checked in the service layer before any association
is written.

## API decisions

- `/api/v1/tags/dimensions` manages dimensions.
- `/api/v1/tags` manages tags.
- Transaction create/update payloads use `tag_ids` and responses expose `tags`.
- Transaction list filtering supports `tag_ids`, `tag_match=all|any`, and
  `exclude_tag_ids`.
- `/api/v1/aggregations/views` manages views and nested nodes.
- `/api/v1/aggregations/views/{id}/results` evaluates the tree for a date range and
  movement type.

## Rejected alternatives

### Keep categories and add tags

This preserves an additive primary classification, but leaves users deciding which
concept belongs in the category path and which belongs in tags. It also keeps two
management systems for a pre-production product whose primary requirement is
multidimensional reporting.

### Unlimited category hierarchy

It adds depth but still provides only one path per transaction. It cannot express
several independent views without duplication.

### Store aggregation membership on transactions

Aggregation nodes are derived views, not transaction facts. Persisting membership
would duplicate data and require expensive synchronization after every rule edit.

## Consequences

### Positive

- Atomic facts can be combined in any order.
- Users can create several nested views over the same transactions.
- Adding reporting depth does not alter transaction storage.
- `EXISTS` predicates prevent duplicate rows from multiplying monetary totals.

### Negative

- Tag reports can overlap, so child totals do not always sum to their parent.
- Assignment validation is more involved for single-select dimensions.
- Evaluating many nodes requires multiple aggregate queries initially.

## Evolution

If a view approaches the 100-node limit or result latency becomes material, batch
the node predicates into fewer SQL statements or add a cache keyed by user, view,
filter range, and the latest transaction/tag update timestamp. Do not precompute
aggregation membership until measurements justify the operational complexity.
