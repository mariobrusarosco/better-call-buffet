"""add transactions table - focused migration

Revision ID: add_transactions_table_focused
Revises: focused_broker_logo_nullable
Create Date: 2025-06-30 20:20:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_transactions_table_focused"
down_revision: Union[str, None] = "focused_broker_logo_nullable"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Create transactions table."""
    # Only create the transactions table
    op.create_table(
        "transactions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=True),
        sa.Column("credit_card_id", sa.UUID(), nullable=True),
        sa.Column("broker_id", sa.UUID(), nullable=True),
        sa.Column("is_paid", sa.Boolean(), nullable=True),
        sa.Column("date", sa.DateTime(), nullable=True),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("movement_type", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["broker_id"],
            ["brokers.id"],
        ),
        sa.ForeignKeyConstraint(
            ["credit_card_id"],
            ["credit_cards.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema - Drop transactions table."""
    # Remove the transactions table
    op.drop_table("transactions")
