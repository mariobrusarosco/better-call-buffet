"""Merge categories migration with balance points hotfix

Revision ID: 9988dbfb0e7d
Revises: 67991428e02a, a6826185c146
Create Date: 2025-12-23 14:59:49.485618

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9988dbfb0e7d'
down_revision: Union[str, None] = ('67991428e02a', 'a6826185c146')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
