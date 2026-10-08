# Tag Groups Domain

**Decision record:** `docs/decisions/010-flat-tags-and-tag-groups.md`

## Purpose

A tag group is a saved combination of tags, e.g. "Mother Health Expenses" =
`health` + `mother`. Groups can nest; a child inherits its parent's tags.

| Group | Own tags | Matches (effective tags) |
|---|---|---|
| Health Expenses | `health` | `health` |
| └ Personal Health | `personal` | `health` + `personal` |
| └ Mother Health Expenses | `mother` | `health` + `mother` |

## Data model

- `tag_groups`: `id`, `user_id`, `parent_id` (self FK, `ON DELETE CASCADE`),
  `name` (≤120), `display_order`, timestamps.
- `tag_group_tags`: `(group_id, tag_id)` primary key, both FKs cascade.

Effective tags are never stored; they are derived from the parent chain on read.

## API (`/api/v1/tag-groups`)

| Method | Path | Notes |
|---|---|---|
| GET | `/tag-groups` | Flat list ordered by `display_order`, `name`. The client nests by `parent_id`. |
| POST | `/tag-groups` | `{name, tag_ids, parent_id?, display_order?}` → 201 |
| PATCH | `/tag-groups/{id}` | Any of `name`, `tag_ids`, `parent_id`, `display_order`. `parent_id: null` moves to the top level. |
| DELETE | `/tag-groups/{id}` | 204. Deletes the subtree. |
| GET | `/tag-groups/summary` | `[{group_id, total, count}]` for every group |
| GET | `/tag-groups/overlaps` | `[{transaction_id, description, amount, date, group_ids}]` |

Response item:

```jsonc
{
  "id": "uuid",
  "name": "Mother Health Expenses",
  "parent_id": "uuid-of-Health",      // or null
  "tag_ids": ["mother"],               // own tags
  "effective_tag_ids": ["health", "mother"], // ancestors first, read-only
  "display_order": 0,
  "created_at": "…",
  "updated_at": "…"
}
```

`summary` and `overlaps` accept `date_from`, `date_to` (inclusive datetimes) and
`movement_type` (default `expense`). Both cover all matching transactions, with no
pagination, and skip deleted and ignored transactions, like Cashflow does.
`total` and `amount` are decimal strings.

In `overlaps`, `group_ids` lists the **most specific** groups sharing the
transaction. An ancestor implied by a listed child is left out.

## Validation

| Rule | Error code |
|---|---|
| `name` required, not blank | `VALIDATION_ERROR` (422) |
| 1–20 unique `tag_ids` | `VALIDATION_ERROR` (422) |
| Tags exist, are active and belong to the user | `INVALID_TAG_ASSIGNMENT` |
| Parent exists and belongs to the user | `INVALID_TAG_GROUP_PARENT` |
| No moving a group under itself or a descendant | `TAG_GROUP_CYCLE` |
| At most 8 levels, counting the whole moved subtree | `TAG_GROUP_DEPTH_EXCEEDED` |
| Unknown group id | `TAG_GROUP_NOT_FOUND` (404) |

## Layers

- `service.py`: tree rules plus the pure helpers `ancestor_ids`,
  `effective_tag_ids` and `most_specific_groups` (unit tested without a database).
- `repository.py`: `_scoped_transactions` is the single place that defines which
  transactions count, shared by the summary and overlap queries.
- Tests: `tests/domains/tag_groups/` (unit + Postgres integration with rollback).
