"""replace tag groups with cashflow views

Tag groups (nested, matching transactions that carry ALL of a group's tags)
are replaced by cashflow views: named views holding flat groups, each
matching transactions that carry ANY of its tags.

The two match rules differ, so existing tag groups are not converted:
dropping tag_groups deletes their rows. The downgrade recreates the tables
empty; that data cannot be restored.

Revision ID: aa6c7cf01e3d
Revises: 5023d16fc221
Create Date: 2026-10-18

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "aa6c7cf01e3d"
down_revision: Union[str, None] = "5023d16fc221"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cashflow_views",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cashflow_views_user_id", "cashflow_views", ["user_id"], unique=False
    )

    op.create_table(
        "cashflow_view_groups",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("view_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["view_id"], ["cashflow_views.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cashflow_view_groups_view_position",
        "cashflow_view_groups",
        ["view_id", "position"],
        unique=False,
    )

    op.create_table(
        "cashflow_view_group_tags",
        sa.Column("group_id", sa.UUID(), nullable=False),
        sa.Column("tag_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["group_id"], ["cashflow_view_groups.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("group_id", "tag_id"),
    )
    op.create_index(
        "ix_cashflow_view_group_tags_tag_group",
        "cashflow_view_group_tags",
        ["tag_id", "group_id"],
        unique=False,
    )

    # Link table first: it references tag_groups.
    op.drop_index("ix_tag_group_tags_tag_group", table_name="tag_group_tags")
    op.drop_table("tag_group_tags")
    op.drop_index("ix_tag_groups_user_parent", table_name="tag_groups")
    op.drop_table("tag_groups")


def downgrade() -> None:
    op.create_table(
        "tag_groups",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["tag_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tag_groups_user_parent",
        "tag_groups",
        ["user_id", "parent_id"],
        unique=False,
    )

    op.create_table(
        "tag_group_tags",
        sa.Column("group_id", sa.UUID(), nullable=False),
        sa.Column("tag_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["tag_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("group_id", "tag_id"),
    )
    op.create_index(
        "ix_tag_group_tags_tag_group",
        "tag_group_tags",
        ["tag_id", "group_id"],
        unique=False,
    )

    # Children before parents.
    op.drop_index(
        "ix_cashflow_view_group_tags_tag_group", table_name="cashflow_view_group_tags"
    )
    op.drop_table("cashflow_view_group_tags")
    op.drop_index(
        "ix_cashflow_view_groups_view_position", table_name="cashflow_view_groups"
    )
    op.drop_table("cashflow_view_groups")
    op.drop_index("ix_cashflow_views_user_id", table_name="cashflow_views")
    op.drop_table("cashflow_views")
