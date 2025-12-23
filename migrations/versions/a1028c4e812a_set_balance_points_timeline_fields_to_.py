"""Set balance_points timeline fields to NOT NULL after backfill

Revision ID: a1028c4e812a
Revises: 9988dbfb0e7d
Create Date: 2025-12-23 15:02:45.617272

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1028c4e812a'
down_revision: Union[str, None] = '9988dbfb0e7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Set columns to NOT NULL after backfill
    # These columns were added as nullable in e495b5c46617
    # Then backfilled with defaults in 36d517006667 hotfix
    # Now we can safely set them to NOT NULL
    op.alter_column('balance_points', 'timeline_status',
               existing_type=sa.String(),
               nullable=False)
    op.alter_column('balance_points', 'has_transactions',
               existing_type=sa.Boolean(),
               nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Revert to nullable
    op.alter_column('balance_points', 'timeline_status',
               existing_type=sa.String(),
               nullable=True)
    op.alter_column('balance_points', 'has_transactions',
               existing_type=sa.Boolean(),
               nullable=True)
