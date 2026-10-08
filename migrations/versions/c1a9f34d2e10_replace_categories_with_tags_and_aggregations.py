"""replace categories with tags and aggregation trees

Revision ID: c1a9f34d2e10
Revises: 80d2c00a935a
Create Date: 2026-10-08

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c1a9f34d2e10"
down_revision: Union[str, None] = "80d2c00a935a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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

    op.create_table(
        "tags",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("dimension_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("normalized_name", sa.String(length=100), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["dimension_id"], ["tag_dimensions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "normalized_name", name="uq_tags_user_normalized_name"
        ),
    )
    op.create_index(
        "ix_tags_user_active", "tags", ["user_id", "is_active"], unique=False
    )
    op.create_index(
        "ix_tags_user_dimension", "tags", ["user_id", "dimension_id"], unique=False
    )

    op.create_table(
        "transaction_tags",
        sa.Column("transaction_id", sa.UUID(), nullable=False),
        sa.Column("tag_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["transaction_id"], ["transactions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("transaction_id", "tag_id"),
    )
    op.create_index(
        "ix_transaction_tags_tag_transaction",
        "transaction_tags",
        ["tag_id", "transaction_id"],
        unique=False,
    )

    op.create_table(
        "subscription_tags",
        sa.Column("subscription_id", sa.UUID(), nullable=False),
        sa.Column("tag_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["subscription_id"], ["subscriptions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("subscription_id", "tag_id"),
    )
    op.create_index(
        "ix_subscription_tags_tag_subscription",
        "subscription_tags",
        ["tag_id", "subscription_id"],
        unique=False,
    )

    op.create_table(
        "installment_plan_tags",
        sa.Column("installment_plan_id", sa.UUID(), nullable=False),
        sa.Column("tag_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["installment_plan_id"], ["installment_plans.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("installment_plan_id", "tag_id"),
    )
    op.create_index(
        "ix_installment_plan_tags_tag_plan",
        "installment_plan_tags",
        ["tag_id", "installment_plan_id"],
        unique=False,
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
        "ix_aggregation_views_user",
        "aggregation_views",
        ["user_id"],
        unique=False,
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

    op.drop_constraint(
        "transactions_category_id_fkey", "transactions", type_="foreignkey"
    )
    op.drop_constraint(
        "subscriptions_category_id_fkey", "subscriptions", type_="foreignkey"
    )
    op.drop_constraint(
        "installment_plans_category_id_fkey",
        "installment_plans",
        type_="foreignkey",
    )
    op.drop_column("transactions", "category_id")
    op.drop_column("transactions", "category")
    op.drop_column("subscriptions", "category_id")
    op.drop_column("installment_plans", "category_id")

    op.drop_index("ix_user_categories_user_id", table_name="user_categories")
    op.drop_index("ix_user_categories_id", table_name="user_categories")
    op.drop_index("idx_user_categories_user_parent", table_name="user_categories")
    op.drop_index("idx_user_categories_user_active", table_name="user_categories")
    op.drop_table("user_categories")


def downgrade() -> None:
    op.create_table(
        "user_categories",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["parent_id"], ["user_categories.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "name", "parent_id", name="uq_user_category_name"
        ),
    )
    op.create_index(
        "idx_user_categories_user_active",
        "user_categories",
        ["user_id", "is_active"],
        unique=False,
    )
    op.create_index(
        "idx_user_categories_user_parent",
        "user_categories",
        ["user_id", "parent_id"],
        unique=False,
    )
    op.create_index("ix_user_categories_id", "user_categories", ["id"], unique=False)
    op.create_index(
        "ix_user_categories_user_id", "user_categories", ["user_id"], unique=False
    )

    op.add_column("transactions", sa.Column("category", sa.String(), nullable=True))
    op.add_column("transactions", sa.Column("category_id", sa.UUID(), nullable=True))
    op.add_column("subscriptions", sa.Column("category_id", sa.UUID(), nullable=True))
    op.add_column(
        "installment_plans", sa.Column("category_id", sa.UUID(), nullable=True)
    )
    op.create_foreign_key(
        "transactions_category_id_fkey",
        "transactions",
        "user_categories",
        ["category_id"],
        ["id"],
    )
    op.create_foreign_key(
        "subscriptions_category_id_fkey",
        "subscriptions",
        "user_categories",
        ["category_id"],
        ["id"],
    )
    op.create_foreign_key(
        "installment_plans_category_id_fkey",
        "installment_plans",
        "user_categories",
        ["category_id"],
        ["id"],
    )

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
    op.drop_index(
        "ix_installment_plan_tags_tag_plan", table_name="installment_plan_tags"
    )
    op.drop_table("installment_plan_tags")
    op.drop_index(
        "ix_subscription_tags_tag_subscription", table_name="subscription_tags"
    )
    op.drop_table("subscription_tags")
    op.drop_index("ix_transaction_tags_tag_transaction", table_name="transaction_tags")
    op.drop_table("transaction_tags")
    op.drop_index("ix_tags_user_dimension", table_name="tags")
    op.drop_index("ix_tags_user_active", table_name="tags")
    op.drop_table("tags")
    op.drop_index("ix_tag_dimensions_user_active", table_name="tag_dimensions")
    op.drop_table("tag_dimensions")
