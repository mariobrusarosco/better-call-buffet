"""fix invoices table columns

Revision ID: 0a37f37a027e
Revises: 0c6b2375f86e
Create Date: 2025-06-16 22:23:01.422586

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0a37f37a027e"
down_revision: Union[str, None] = "0c6b2375f86e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
