"""Make description nullable in credit_cards table

Revision ID: 5c226dee95b7
Revises: 66e3a8505488
Create Date: 2025-06-15 09:49:01.063226

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c226dee95b7'
down_revision: Union[str, None] = '66e3a8505488'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make description column nullable."""
    op.alter_column('credit_cards', 'description', nullable=True)


def downgrade() -> None:
    """Make description column non-nullable."""
    op.alter_column('credit_cards', 'description', nullable=False)
