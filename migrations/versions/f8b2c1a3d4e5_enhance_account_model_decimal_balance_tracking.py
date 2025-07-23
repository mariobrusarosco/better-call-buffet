"""Enhance account model with decimal balance and tracking

Revision ID: f8b2c1a3d4e5
Revises: 800438840b88
Create Date: 2025-07-23 13:20:00.000000

"""
from typing import Sequence, Union
from decimal import Decimal

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8b2c1a3d4e5'
down_revision: Union[str, None] = '800438840b88'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Step 1: Add new balance tracking columns
    op.add_column('accounts', sa.Column('last_transaction_id', sa.UUID(), nullable=True))
    op.add_column('accounts', sa.Column('balance_updated_at', sa.DateTime(), nullable=True))
    op.add_column('accounts', sa.Column('available_balance', sa.DECIMAL(precision=15, scale=2), nullable=True))
    
    # Step 2: Add foreign key constraint for last_transaction_id
    op.create_foreign_key('fk_accounts_last_transaction', 'accounts', 'transactions', ['last_transaction_id'], ['id'])
    
    # Step 3: Convert existing balance column from Float to DECIMAL
    # First, update any NULL balances to 0.00
    op.execute("UPDATE accounts SET balance = 0.0 WHERE balance IS NULL")
    
    # Convert balance column to DECIMAL
    op.alter_column('accounts', 'balance', 
                   existing_type=sa.Float(),
                   type_=sa.DECIMAL(precision=15, scale=2),
                   existing_nullable=False,
                   nullable=False)
    
    # Step 4: Initialize available_balance with current balance values
    op.execute("UPDATE accounts SET available_balance = balance")
    op.execute("UPDATE accounts SET balance_updated_at = created_at")
    
    # Step 5: Make available_balance NOT NULL after initialization
    op.alter_column('accounts', 'available_balance', nullable=False)
    op.alter_column('accounts', 'balance_updated_at', nullable=False)
    
    # Step 6: Add database constraints
    op.create_check_constraint('balance_precision', 'accounts', 
                              'balance >= -999999999999999.99 AND balance <= 999999999999999.99')
    
    op.create_check_constraint('available_balance_precision', 'accounts',
                              'available_balance >= -999999999999999.99 AND available_balance <= 999999999999999.99')
    
    # Step 7: Add performance indexes
    op.create_index('ix_accounts_balance_updated', 'accounts', ['balance_updated_at'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index('ix_accounts_balance_updated', 'accounts')
    
    # Drop constraints
    op.drop_constraint('available_balance_precision', 'accounts', type_='check')
    op.drop_constraint('balance_precision', 'accounts', type_='check')
    
    # Drop foreign key constraint
    op.drop_constraint('fk_accounts_last_transaction', 'accounts', type_='foreignkey')
    
    # Revert balance column to Float
    op.alter_column('accounts', 'balance',
                   existing_type=sa.DECIMAL(precision=15, scale=2),
                   type_=sa.Float(),
                   existing_nullable=False,
                   nullable=False)
    
    # Drop new columns
    op.drop_column('accounts', 'available_balance')
    op.drop_column('accounts', 'balance_updated_at')
    op.drop_column('accounts', 'last_transaction_id')