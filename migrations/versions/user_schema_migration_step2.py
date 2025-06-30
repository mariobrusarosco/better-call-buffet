"""user schema migration step 2 - finalize schema changes

Revision ID: user_schema_migration_step2
Revises: user_schema_migration_step1
Create Date: 2025-06-30 20:35:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "user_schema_migration_step2"
down_revision: Union[str, None] = "user_schema_migration_step1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Step 2: Finalize schema - make hashed_password NOT NULL and drop old name column."""

    # Step 2a: Make hashed_password NOT NULL (safe now because we set defaults in step 1)
    op.alter_column("users", "hashed_password", nullable=False)

    # Step 2b: Drop the old 'name' column (data already migrated to 'full_name')
    op.drop_column("users", "name")


def downgrade() -> None:
    """Reverse step 2 changes."""
    # Add back the old name column
    op.add_column("users", sa.Column("name", sa.String(), nullable=False))

    # Copy data back from full_name to name
    op.execute("UPDATE users SET name = full_name WHERE full_name IS NOT NULL")

    # Make hashed_password nullable again
    op.alter_column("users", "hashed_password", nullable=True)
