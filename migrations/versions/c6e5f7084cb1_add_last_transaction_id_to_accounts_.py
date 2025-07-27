"""Add last_transaction_id to accounts table

Revision ID: c6e5f7084cb1
Revises: 001_create_base_tables
Create Date: 2025-07-27 12:16:08.399431

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6e5f7084cb1'
down_revision: Union[str, None] = '001_create_base_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add last_transaction_id column to accounts table."""
    # Add the missing column
    op.add_column('accounts', sa.Column('last_transaction_id', sa.UUID(), nullable=True))
    
    # Add the foreign key constraint
    op.create_foreign_key(
        'fk_accounts_last_transaction_id', 
        'accounts', 
        'transactions',
        ['last_transaction_id'], 
        ['id']
    )


def downgrade() -> None:
    """Remove last_transaction_id column from accounts table."""
    # Drop the foreign key constraint first
    op.drop_constraint('fk_accounts_last_transaction_id', 'accounts', type_='foreignkey')
    
    # Drop the column
    op.drop_column('accounts', 'last_transaction_id')
