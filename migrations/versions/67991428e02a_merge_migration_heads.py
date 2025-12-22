"""Merge migration heads

Revision ID: 67991428e02a
Revises: 36d517006667, 928971a0a0f3
Create Date: 2025-12-22 21:20:39.502421

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '67991428e02a'
down_revision: Union[str, None] = ('36d517006667', '928971a0a0f3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
