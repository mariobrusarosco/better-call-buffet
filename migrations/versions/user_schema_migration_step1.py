"""user schema migration step 1 - add new columns safely

Revision ID: user_schema_migration_step1  
Revises: add_transactions_table_focused
Create Date: 2025-06-30 20:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "user_schema_migration_step1"
down_revision: Union[str, None] = "add_transactions_table_focused"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Step 1: Add new columns safely as nullable, migrate data."""

    # Step 1a: Add new columns as nullable (safe for existing data)
    op.add_column("users", sa.Column("full_name", sa.String(), nullable=True))
    op.add_column(
        "users", sa.Column("hashed_password", sa.String(), nullable=True)
    )  # nullable first!

    # Step 1b: Copy data from 'name' to 'full_name'
    op.execute("UPDATE users SET full_name = name WHERE name IS NOT NULL")

    # Step 1c: Set default password for existing users (you might want to customize this)
    op.execute(
        "UPDATE users SET hashed_password = 'CHANGE_ME_' || id::text WHERE hashed_password IS NULL"
    )

    # Step 1d: Update timestamp constraints to NOT NULL
    op.alter_column("users", "is_active", nullable=False)
    op.alter_column("users", "created_at", nullable=False)
    op.alter_column("users", "updated_at", nullable=False)

    # Step 1e: Add proper indexes
    op.create_index("ix_users_created_at", "users", ["created_at"], unique=False)
    op.create_unique_constraint("uq_users_email", "users", ["email"])


def downgrade() -> None:
    """Reverse step 1 changes."""
    # Remove constraints and indexes
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.drop_index("ix_users_created_at", table_name="users")

    # Revert column constraints
    op.alter_column("users", "updated_at", nullable=True)
    op.alter_column("users", "created_at", nullable=True)
    op.alter_column("users", "is_active", nullable=True)

    # Remove new columns
    op.drop_column("users", "hashed_password")
    op.drop_column("users", "full_name")
