"""Add user_id column to credit_cards table

Revision ID: 66e3a8505488
Revises: 4714248eb752
Create Date: 2025-06-15 09:39:28.031251

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "66e3a8505488"
down_revision: Union[str, None] = "4714248eb752"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add user_id column to credit_cards table
    op.add_column(
        "credit_cards", sa.Column("user_id", postgresql.UUID(), nullable=False)
    )
    op.create_foreign_key(
        "fk_credit_cards_user_id", "credit_cards", "users", ["user_id"], ["id"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove user_id column from credit_cards table
    op.drop_constraint("fk_credit_cards_user_id", "credit_cards", type_="foreignkey")
    op.drop_column("credit_cards", "user_id")
