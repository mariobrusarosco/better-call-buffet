# Tag Classification Migration Guide

This is a clean-break migration for a pre-production project. It preserves core
financial records but intentionally removes the category API and category columns.

## Upgrade order

1. Create `tag_dimensions`, `tags`, and the three assignment tables.
2. Create aggregation views, nodes, and conditions.
3. Drop category foreign keys and columns from transactions, subscriptions, and
   installment plans.
4. Drop `user_categories`.
5. Deploy the tag and aggregation API together with the migration.

The migration does not infer tags from old category paths. The product has no
production compatibility requirement, and automatic conversion would incorrectly
guess whether a path component means purpose, beneficiary, context, or something
else.

## Verification

```bash
docker compose exec web alembic upgrade head
docker compose exec web alembic current
docker compose exec web poetry run pytest
docker compose exec web poetry run mypy app
docker compose exec web poetry run flake8
```

Verify manually that:

- `user_categories` no longer exists.
- No `category` or `category_id` column remains on transaction/template tables.
- Tag assignments reject another user's tags.
- A single-select dimension rejects two selected values.
- Moving a node cannot create a cycle or exceed depth 8.
- Aggregation totals count a transaction only once per node.
- CSV export/import round-trips tag names.

## Downgrade

The downgrade recreates the old category tables and nullable category columns, but
it cannot reconstruct old category assignments because the upgrade intentionally
does not map category paths. Tag and aggregation data is removed on downgrade.
