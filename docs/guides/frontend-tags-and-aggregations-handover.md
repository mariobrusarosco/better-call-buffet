# Frontend Handover: Categories to Tags and Aggregation Views

> **Superseded (2026-10-08):** tag dimensions and aggregation views were removed.
> See `docs/decisions/010-flat-tags-and-tag-groups.md` and `docs/domains/tag-groups.md`.

**Backend status:** Implemented
**API prefix:** `/api/v1`
**Compatibility:** Clean break; the category API and category fields no longer exist

## What changed

Categories previously mixed two concerns:

1. facts attached to a financial record; and
2. the hierarchy used to present totals.

They are now separate:

- **Tags** are flat facts attached to transactions, subscriptions, and installment
  plans. Example: `Health`, `Mother`, `Medication`.
- **Tag dimensions** optionally group tags and control whether one or several tags
  may be selected. Example: a single-select `Person` dimension containing
  `Mother` and `Myself`.
- **Aggregation views** are user-defined reporting trees. Each node contains tag
  conditions and inherits the conditions of its ancestors.

Example:

```text
Health Expenses [Health]
├── Health and Mother [Mother]
└── Health and Myself [Myself]
```

The two child rules are effectively `Health AND Mother` and
`Health AND Myself`. The child payloads should not repeat the inherited `Health`
condition.

## Required frontend removals

Remove all code that depends on:

- `GET|POST|PATCH|DELETE /api/v1/categories`
- `category`
- `category_id`
- `category_tree`
- category dropdowns and two-level category tree components
- category-based transaction filters and category sort options
- `category_breakdown` in subscription summaries
- `category_name` and `category_parent` in CSV help/templates

There is no compatibility endpoint or transitional response field.

## Contract mapping

| Previous concept | Replacement |
| --- | --- |
| One `category_id` on a transaction | `tag_ids: string[]` in requests |
| Nested category response | `tags: Tag[]` in responses |
| Category selector | Dimension-grouped tag selector |
| Category transaction filter | `tag_ids` + `tag_match` + `exclude_tag_ids` |
| Category hierarchy | Aggregation view and nested nodes |
| Category breakdown | `tag_breakdown` |
| CSV category fields | `tag_names`, encoded as a JSON string array |

## Suggested TypeScript types

```ts
export type TagSelectionMode = "single" | "multiple";

export interface TagDimension {
  id: string;
  user_id: string;
  name: string;
  selection_mode: TagSelectionMode;
  display_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Tag {
  id: string;
  user_id: string;
  name: string;
  dimension_id: string | null;
  display_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  dimension: TagDimension | null;
}

export type AggregationOperator = "include" | "exclude";

export interface AggregationCondition {
  id: string;
  tag_id: string;
  operator: AggregationOperator;
  tag: Tag;
}

export interface AggregationNode {
  id: string;
  view_id: string;
  parent_id: string | null;
  name: string;
  display_order: number;
  conditions: AggregationCondition[];
  children: AggregationNode[];
  created_at: string;
  updated_at: string;
}

export interface AggregationViewSummary {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface AggregationView extends AggregationViewSummary {
  nodes: AggregationNode[];
}

export interface AggregationNodeResult {
  node_id: string;
  name: string;
  total: string; // Decimal is serialized as a JSON string
  transaction_count: number;
  children: AggregationNodeResult[];
}

export interface AggregationViewResult {
  view_id: string;
  name: string;
  nodes: AggregationNodeResult[];
}
```

Generated API types should be preferred if the frontend already generates clients
from OpenAPI.

## Tags API

### Dimensions

```text
GET    /api/v1/tags/dimensions?include_inactive=false
POST   /api/v1/tags/dimensions
PATCH  /api/v1/tags/dimensions/{dimension_id}
DELETE /api/v1/tags/dimensions/{dimension_id}
```

Create request:

```json
{
  "name": "Person",
  "selection_mode": "single",
  "display_order": 0
}
```

`GET` returns a raw `TagDimension[]`. Deleting a dimension returns `204` and is
allowed only after all of its tags have been deactivated or moved.

### Tags

```text
GET    /api/v1/tags?dimension_id={optional}&include_inactive=false
POST   /api/v1/tags
PATCH  /api/v1/tags/{tag_id}
DELETE /api/v1/tags/{tag_id}
```

Create request:

```json
{
  "name": "Mother",
  "dimension_id": "person-dimension-id",
  "display_order": 0
}
```

`GET` returns a raw `Tag[]`. `dimension_id` may be `null` for an ungrouped tag.
For PATCH requests:

- omit `dimension_id` to preserve it;
- send `dimension_id: null` to move the tag to the ungrouped section.

Deleting a tag is a soft deletion and returns `204`. Existing transaction responses
may still contain that inactive tag, but it cannot be assigned again.

## Tag selection UI

The recommended selector is a grouped chip/combobox UI:

- Group tags by `dimension` and order groups and tags by `display_order`, then name.
- Render a single-select dimension like a radio group or single-value combobox.
- Render a multiple-select dimension and ungrouped tags as checkboxes/chips.
- Enforce the global maximum of 20 selected tags.
- Send tag IDs only; never send tag names as transaction classification.
- Display nested `tags` from responses so renamed or inactive tags remain readable.

When PATCHing an entity, `tag_ids` is replacement semantics:

- omitted: preserve existing tags;
- `[]`: clear all tags;
- non-empty array: replace the complete assignment.

Do not submit an unchanged full tag list during unrelated edits. An old inactive
tag is readable but no longer assignable, so resubmitting it will be rejected.

## Transaction contract changes

Transaction create, update, bulk create, bulk update, and response contracts now
use tags.

Request fragment:

```json
{
  "description": "Doctor appointment",
  "amount": 250.0,
  "tag_ids": ["health-tag-id", "mother-tag-id"]
}
```

Response fragment:

```json
{
  "tag_ids": ["health-tag-id", "mother-tag-id"],
  "tags": [
    {
      "id": "health-tag-id",
      "name": "Health",
      "dimension_id": "topic-dimension-id",
      "is_active": true,
      "dimension": {
        "id": "topic-dimension-id",
        "name": "Topic",
        "selection_mode": "single"
      }
    }
  ]
}
```

The example is abbreviated; timestamps, ownership, and display-order fields are
also returned.

### Transaction filtering

`GET /api/v1/transactions` supports:

```text
tag_ids=id-1&tag_ids=id-2&tag_match=all
tag_ids=id-1&tag_ids=id-2&tag_match=any
exclude_tag_ids=id-3
```

- `all`: every selected tag is required.
- `any`: at least one selected tag is required.
- `exclude_tag_ids`: every returned transaction must omit those tags.

Repeated query parameters work consistently and should be preferred by the API
client. The main transaction endpoint also accepts comma-separated IDs.

The account and credit-card transaction routes expose the same tag filters. Remove
`category` from their query state and remove `category` from allowed sort values.

## Subscription and installment-plan changes

Subscription and installment-plan create/response schemas use the same
`tag_ids`/`tags` pattern. List endpoints accept `tag_ids` and `tag_match=all|any`.

When a subscription payment or installment is linked to a transaction, the
template's tags are copied onto that transaction.

Subscription summaries now return:

```ts
interface SubscriptionSummary {
  monthly_burn_rate: number;
  yearly_projection: number;
  due_next_30_days: number;
  active_count: number;
  tag_breakdown: Array<{ name: string; amount: number }>;
  monthly_forecast: Array<{ month: string; amount: number }>;
}
```

Because a subscription may have several tags, `tag_breakdown` entries can overlap
and must not be summed to derive the burn rate.

## Aggregation views API

### View CRUD

```text
GET    /api/v1/aggregations/views
POST   /api/v1/aggregations/views
GET    /api/v1/aggregations/views/{view_id}
PATCH  /api/v1/aggregations/views/{view_id}
DELETE /api/v1/aggregations/views/{view_id}
```

List returns `AggregationViewSummary[]`; get returns the full nested tree.

Create request:

```json
{
  "name": "My Expense View",
  "description": "Expenses grouped by topic and person"
}
```

### Node CRUD

```text
POST   /api/v1/aggregations/views/{view_id}/nodes
PATCH  /api/v1/aggregations/views/{view_id}/nodes/{node_id}
DELETE /api/v1/aggregations/views/{view_id}/nodes/{node_id}
```

Every node mutation returns the complete updated `AggregationView`. Use that
response to replace the cached tree instead of issuing an immediate extra GET.

Create the root:

```json
{
  "name": "Health Expenses",
  "parent_id": null,
  "display_order": 0,
  "conditions": [
    {"tag_id": "health-tag-id", "operator": "include"}
  ]
}
```

Create a child:

```json
{
  "name": "Health and Mother",
  "parent_id": "health-root-node-id",
  "display_order": 0,
  "conditions": [
    {"tag_id": "mother-tag-id", "operator": "include"}
  ]
}
```

PATCH uses partial-update semantics:

- omit `parent_id` to keep the current parent;
- send `parent_id: null` to make the node a root;
- omit `conditions` to preserve them;
- send `conditions: []` to make the node add no conditions.

Deleting a node also deletes its descendants. The UI should require confirmation
when the node has children.

### Results

```text
GET /api/v1/aggregations/views/{view_id}/results
```

Optional repeated query parameters:

```text
date_from=2026-01-01T00:00:00
date_to=2026-12-31T23:59:59
movement_type=expense
movement_type=investment
```

Without `movement_type`, results default to expenses.

Example response:

```json
{
  "view_id": "view-id",
  "name": "My Expense View",
  "nodes": [
    {
      "node_id": "health-root-node-id",
      "name": "Health Expenses",
      "total": "150.00",
      "transaction_count": 2,
      "children": [
        {
          "node_id": "mother-node-id",
          "name": "Health and Mother",
          "total": "100.00",
          "transaction_count": 1,
          "children": []
        },
        {
          "node_id": "myself-node-id",
          "name": "Health and Myself",
          "total": "50.00",
          "transaction_count": 1,
          "children": []
        }
      ]
    }
  ]
}
```

Render totals returned by the backend. Do not calculate a parent by summing its
children: sibling nodes may overlap, and transactions that match the parent may be
unmatched by every child.

## Aggregation editor rules

The frontend should prevent invalid edits when practical, while still displaying
backend errors:

- Maximum 100 nodes per view.
- Maximum depth 8; root is depth 1.
- Sibling names must be unique case-insensitively.
- A node cannot become its own ancestor.
- A node cannot include and exclude the same effective tag path.
- One node cannot repeat a tag condition.
- Conditions may reference only active tags owned by the user.
- `include` conditions require a tag; `exclude` conditions reject a tag.

## Error handling

New tag and aggregation endpoints use the standard error envelope:

```json
{
  "error": {
    "code": "TAG_DIMENSION_ASSIGNMENT_CONFLICT",
    "message": "Only one tag may be selected from a single-select dimension",
    "request_id": "request-id",
    "timestamp": null
  }
}
```

`details` is optional and appears when the backend has structured context to add.

Important codes include:

- `TAG_ALREADY_EXISTS`
- `TAG_DIMENSION_ALREADY_EXISTS`
- `TAG_LIMIT_EXCEEDED`
- `DUPLICATE_TAG_IDS`
- `INVALID_TAG_ASSIGNMENT`
- `TAG_DIMENSION_ASSIGNMENT_CONFLICT`
- `AGGREGATION_NODE_LIMIT_EXCEEDED`
- `AGGREGATION_DEPTH_EXCEEDED`
- `AGGREGATION_NODE_CYCLE`
- `DUPLICATE_AGGREGATION_NODE_NAME`
- `CONTRADICTORY_AGGREGATION_CONDITIONS`
- `INVALID_AGGREGATION_TAG`

Schema validation also returns HTTP `422` with code `VALIDATION_ERROR` and field
details. Some older subscription/installment routers still translate domain errors
to HTTP `400`, so the shared API error handler should support both statuses.

## CSV and AI-related UI changes

- CSV now uses one `tag_names` cell containing a JSON array such as
  `["Health", "Mother"]`.
- Remove `category_name` and `category_parent` from downloadable templates and
  import documentation.
- CSV imports reject duplicate tag names and more than 20 tags on one row.
- Parsed AI transaction suggestions now expose `tags: string[]` instead of a
  `category` string.

## Cache invalidation guidance

- Tag create/update/delete: invalidate tag lists. A rename should also refresh
  visible transactions and aggregation definitions that display nested tag data.
- Dimension changes: invalidate dimensions and tag lists.
- Transaction tag changes: invalidate transaction lists and aggregation results.
- Node mutation: replace the cached view with the returned view and invalidate its
  results.
- Tag deactivation: keep rendering nested inactive tags already returned on old
  records.

## Recommended implementation order

1. Delete Category API types, hooks, stores, routes, and components.
2. Add Tag, TagDimension, and aggregation API types/client functions.
3. Build tag and dimension management in settings.
4. Replace transaction category inputs with the dimension-grouped tag selector.
5. Replace transaction category filters with all/any/exclude tag filtering.
6. Update subscription and installment-plan forms and summary rendering.
7. Build the aggregation view selector, tree editor, and results tree.
8. Update CSV instructions and AI suggestion rendering.
9. Add cache invalidation and error-code mapping.
10. Remove all remaining frontend references to `category`, `category_id`, and
    `/categories`.

## Frontend acceptance checklist

- A user can create `Health`, `Mother`, and `Myself` tags.
- A transaction can be saved with `Health + Mother`.
- A transaction can be saved with `Health + Myself`.
- A single-select dimension prevents selecting both `Mother` and `Myself`.
- Editing a non-tag transaction field preserves its existing tags.
- Clearing the selector sends `tag_ids: []`.
- Transaction filters support both `all` and `any` matching.
- The user can create a Health root with Mother and Myself children.
- The results screen renders the nested totals returned by the backend.
- Moving a node to the root sends `parent_id: null`.
- Deleting a parent warns that its descendants will also be deleted.
- Inactive historical tags remain readable.
- No network request targets `/api/v1/categories`.
- No frontend type or state field references `category_id` or `category_tree`.
