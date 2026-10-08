# Tags and Aggregations Domain

**Frontend integration:** See
`docs/guides/frontend-tags-and-aggregations-handover.md`.

## Purpose

Tags store atomic facts about financial records. Aggregation views turn those facts
into reusable nested reports.

```text
Transaction: Health, Mother, Medication

Health Expenses [Health]
└── Mother [Mother]
    └── Medication [Medication]
```

The leaf matches `Health AND Mother AND Medication` because node conditions are
inherited from every ancestor.

## Domain rules

### Dimensions

- `single` dimensions allow at most one active tag from that dimension on an
  entity. Example: a `Beneficiary` dimension may contain `Mother`, `Myself`, and
  `Household`.
- `multiple` dimensions allow any number of their tags.
- Tags may be ungrouped by leaving `dimension_id` null.
- Dimensions can only be deactivated when they have no active tags.

### Tags

- Names are trimmed and normalized with `casefold()`.
- A user cannot create two active or inactive tags with the same normalized name.
- Deactivation preserves existing assignments and report definitions.
- Inactive tags cannot be newly assigned.

### Assignments

- Every referenced tag must belong to the authenticated user and be active.
- Duplicate IDs are rejected.
- At most 20 tags may be assigned.
- A proposed assignment is validated as one complete set, which makes replacement
  updates deterministic.
- Subscription and installment-plan tags are templates. They are copied to linked
  or generated transactions by the relevant workflow; reports always read the
  tags attached to transactions.

### Aggregation trees

- A view may contain at most 100 nodes.
- A node may be moved, but not below itself or one of its descendants.
- Maximum depth is 8, with a root node at depth 1.
- A condition is unique per node and tag.
- A condition may include or exclude its tag.
- Contradictory effective paths are rejected when detected.

## Query semantics

The effective condition set for a node is collected from the path from the root to
that node. Each included tag becomes a correlated `EXISTS` predicate and each
excluded tag becomes `NOT EXISTS`. This avoids joining tag rows into the monetary
aggregate and guarantees that one transaction contributes at most once per node.

Aggregation results exclude ignored and soft-deleted transactions. They default to
expense movements and may be bounded by date.

## Main API contracts

```text
POST   /api/v1/tags/dimensions
GET    /api/v1/tags/dimensions
PATCH  /api/v1/tags/dimensions/{dimension_id}
DELETE /api/v1/tags/dimensions/{dimension_id}

POST   /api/v1/tags
GET    /api/v1/tags
PATCH  /api/v1/tags/{tag_id}
DELETE /api/v1/tags/{tag_id}

POST   /api/v1/aggregations/views
GET    /api/v1/aggregations/views
GET    /api/v1/aggregations/views/{view_id}
PATCH  /api/v1/aggregations/views/{view_id}
DELETE /api/v1/aggregations/views/{view_id}

POST   /api/v1/aggregations/views/{view_id}/nodes
PATCH  /api/v1/aggregations/views/{view_id}/nodes/{node_id}
DELETE /api/v1/aggregations/views/{view_id}/nodes/{node_id}
GET    /api/v1/aggregations/views/{view_id}/results
```

Transaction request example:

```json
{
  "description": "Doctor appointment",
  "amount": 250.00,
  "tag_ids": ["health-id", "mother-id"]
}
```

Aggregation-node request example:

```json
{
  "name": "Mother",
  "parent_id": "health-node-id",
  "conditions": [
    {"tag_id": "mother-tag-id", "operator": "include"}
  ]
}
```

## Index strategy

- `tags(user_id, normalized_name)` is unique.
- `transaction_tags(transaction_id, tag_id)` is the primary key.
- `transaction_tags(tag_id, transaction_id)` supports reverse filtering.
- Equivalent reverse indexes exist for subscription and installment templates.
- Aggregation nodes are indexed by `(view_id, parent_id, display_order)`.
- Conditions are indexed by tag for safe tag-deactivation checks.
