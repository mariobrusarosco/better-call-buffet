"""make broker logo nullable - focused migration

Revision ID: focused_broker_logo_nullable
Revises: 0a37f37a027e
Create Date: 2025-06-30 18:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "focused_broker_logo_nullable"
down_revision: Union[str, None] = "0a37f37a027e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Make broker logo field nullable."""
    # Only change the broker logo field to be nullable
    op.alter_column("brokers", "logo", existing_type=sa.VARCHAR(), nullable=True)


def downgrade() -> None:
    """Downgrade schema - Make broker logo field required again."""
    # Revert broker logo field to be required
    op.alter_column("brokers", "logo", existing_type=sa.VARCHAR(), nullable=False)
