"""add user_id to invoices table

Revision ID: 0c6b2375f86e
Revises: 014a78e888b0
Create Date: 2025-06-16 22:21:02.667577

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0c6b2375f86e"
down_revision: Union[str, None] = "014a78e888b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
