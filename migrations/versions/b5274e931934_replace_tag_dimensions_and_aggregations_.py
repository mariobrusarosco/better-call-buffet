"""replace tag dimensions and aggregation trees with tag groups

Tags become flat (no dimensions, no single-select rule). Aggregation views are
replaced by tag groups: a name plus a list of tags, optionally nested, matching
transactions that carry all of the group's own and inherited tags.

Dropping tag_dimensions and the aggregation tables deletes their rows. The
downgrade recreates the tables empty; that data cannot be restored.

Revision ID: b5274e931934
Revises: c1a9f34d2e10
Create Date: 2026-10-08

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b5274e931934"
down_revision: Union[str, None] = "c1a9f34d2e10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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

    # Aggregation trees: children before parents.
    op.drop_index(
        "ix_aggregation_node_conditions_tag",
        table_name="aggregation_node_conditions",
    )
    op.drop_table("aggregation_node_conditions")
    op.drop_index(
        "ix_aggregation_nodes_view_parent_order", table_name="aggregation_nodes"
    )
    op.drop_table("aggregation_nodes")
    op.drop_index("ix_aggregation_views_user", table_name="aggregation_views")
    op.drop_table("aggregation_views")

    # Dimensions: detach tags first, then drop the table they pointed to.
    op.drop_index("ix_tags_user_dimension", table_name="tags")
    op.drop_constraint("tags_dimension_id_fkey", "tags", type_="foreignkey")
    op.drop_column("tags", "dimension_id")
    op.drop_index("ix_tag_dimensions_user_active", table_name="tag_dimensions")
    op.drop_table("tag_dimensions")


def downgrade() -> None:
    op.create_table(
        "tag_dimensions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("normalized_name", sa.String(length=100), nullable=False),
        sa.Column("selection_mode", sa.String(length=20), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "selection_mode IN ('single', 'multiple')",
            name="ck_tag_dimensions_selection_mode",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "normalized_name",
            name="uq_tag_dimensions_user_normalized_name",
        ),
    )
    op.create_index(
        "ix_tag_dimensions_user_active",
        "tag_dimensions",
        ["user_id", "is_active"],
        unique=False,
    )
    op.add_column("tags", sa.Column("dimension_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "tags_dimension_id_fkey",
        "tags",
        "tag_dimensions",
        ["dimension_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_tags_user_dimension", "tags", ["user_id", "dimension_id"], unique=False
    )

    op.create_table(
        "aggregation_views",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("normalized_name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "normalized_name",
            name="uq_aggregation_views_user_normalized_name",
        ),
    )
    op.create_index(
        "ix_aggregation_views_user", "aggregation_views", ["user_id"], unique=False
    )
    op.create_table(
        "aggregation_nodes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("view_id", sa.UUID(), nullable=False),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["parent_id"], ["aggregation_nodes.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["view_id"], ["aggregation_views.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_aggregation_nodes_view_parent_order",
        "aggregation_nodes",
        ["view_id", "parent_id", "display_order"],
        unique=False,
    )
    op.create_table(
        "aggregation_node_conditions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("node_id", sa.UUID(), nullable=False),
        sa.Column("tag_id", sa.UUID(), nullable=False),
        sa.Column("operator", sa.String(length=10), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "operator IN ('include', 'exclude')",
            name="ck_aggregation_node_conditions_operator",
        ),
        sa.ForeignKeyConstraint(
            ["node_id"], ["aggregation_nodes.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "node_id", "tag_id", name="uq_aggregation_node_conditions_node_tag"
        ),
    )
    op.create_index(
        "ix_aggregation_node_conditions_tag",
        "aggregation_node_conditions",
        ["tag_id"],
        unique=False,
    )

    op.drop_index("ix_tag_group_tags_tag_group", table_name="tag_group_tags")
    op.drop_table("tag_group_tags")
    op.drop_index("ix_tag_groups_user_parent", table_name="tag_groups")
    op.drop_table("tag_groups")
