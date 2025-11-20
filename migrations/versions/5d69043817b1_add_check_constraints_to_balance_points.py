"""Add check constraints 
  to balance_points

Revision ID: 5d69043817b1
Revises: e495b5c46617
Create Date: 2025-11-20 13:42:34.565702

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5d69043817b1'
down_revision: Union[str, None] = 'e495b5c46617'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add check constraint for valid timeline status values
    op.create_check_constraint(
        'ck_valid_timeline_status',
        'balance_points',
        "timeline_status IN ('current', 'updating', 'failed')"
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove check constraint
    op.drop_constraint(
        'ck_valid_timeline_status',
        'balance_points',
        type_='check'
    )