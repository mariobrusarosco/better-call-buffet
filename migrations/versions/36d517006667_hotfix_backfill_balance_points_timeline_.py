"""Hotfix: Backfill balance_points timeline fields before adding constraints

Revision ID: 36d517006667
Revises: 3ba35655589e
Create Date: 2025-12-22 21:12:04.746619

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '36d517006667'
down_revision: Union[str, None] = '3ba35655589e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Backfill timeline_status and has_transactions for existing rows
    op.execute("UPDATE balance_points SET timeline_status = 'current' WHERE timeline_status IS NULL")
    op.execute("UPDATE balance_points SET has_transactions = FALSE WHERE has_transactions IS NULL")


def downgrade() -> None:
    """Downgrade schema."""
    pass
