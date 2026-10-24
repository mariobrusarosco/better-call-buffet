"""cashflow view sub-groups and any/all matching

A group now either holds tags, matching expenses with "any" or "all" of them,
or holds sub-groups (match is NULL). Sub-groups hold tags only, so the tree
is two levels deep at most; the service enforces that.

Existing groups all hold tags and matched ALL of them, so they become
top-level groups with match = 'all': their numbers do not change.

The downgrade deletes sub-groups and the groups that held them, and every
remaining group goes back to matching ALL of its tags, including groups that
were set to "any". That cannot be preserved without the column.

Revision ID: 33615cbf92fd
Revises: aa6c7cf01e3d
Create Date: 2026-10-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "33615cbf92fd"
down_revision: Union[str, None] = "aa6c7cf01e3d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cashflow_view_groups", sa.Column("parent_id", sa.UUID(), nullable=True)
    )
    op.add_column(
        "cashflow_view_groups", sa.Column("match", sa.String(length=3), nullable=True)
    )
    op.execute("UPDATE cashflow_view_groups SET match = 'all'")

    op.create_foreign_key(
        "fk_cashflow_view_groups_parent_id",
        "cashflow_view_groups",
        "cashflow_view_groups",
        ["parent_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_cashflow_view_groups_parent_id",
        "cashflow_view_groups",
        ["parent_id"],
        unique=False,
    )
    op.create_check_constraint(
        "ck_cashflow_view_groups_match",
        "cashflow_view_groups",
        "match IS NULL OR match IN ('any', 'all')",
    )


def downgrade() -> None:
    # Sub-groups first, then the groups that held them (they hold no tags).
    op.execute("DELETE FROM cashflow_view_groups WHERE parent_id IS NOT NULL")
    op.execute("DELETE FROM cashflow_view_groups WHERE match IS NULL")

    op.drop_constraint(
        "ck_cashflow_view_groups_match", "cashflow_view_groups", type_="check"
    )
    op.drop_index(
        "ix_cashflow_view_groups_parent_id", table_name="cashflow_view_groups"
    )
    op.drop_constraint(
        "fk_cashflow_view_groups_parent_id",
        "cashflow_view_groups",
        type_="foreignkey",
    )
    op.drop_column("cashflow_view_groups", "match")
    op.drop_column("cashflow_view_groups", "parent_id")
