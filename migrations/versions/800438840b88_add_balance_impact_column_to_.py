"""Add balance_impact column to transactions

Revision ID: 800438840b88
Revises: c6c5be227b38
Create Date: 2025-07-23 13:03:12.165008

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '800438840b88'
down_revision: Union[str, None] = 'c6c5be227b38'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # CLEAN SLATE APPROACH: Since this is not a live project, clean up any invalid data
    
    # Delete transactions with non-positive amounts (invalid data)
    op.execute("DELETE FROM transactions WHERE amount <= 0")
    
    # Add balance_impact column to track pre-calculated impact on account/credit card balances
    op.add_column('transactions', sa.Column('balance_impact', sa.DECIMAL(precision=15, scale=2), nullable=True))
    
    # Add transfer support columns
    op.add_column('transactions', sa.Column('from_account_id', sa.UUID(), nullable=True))
    op.add_column('transactions', sa.Column('to_account_id', sa.UUID(), nullable=True))
    op.add_column('transactions', sa.Column('related_transaction_id', sa.UUID(), nullable=True))
    
    # Add foreign key constraints for new columns
    op.create_foreign_key('fk_transactions_from_account', 'transactions', 'accounts', ['from_account_id'], ['id'])
    op.create_foreign_key('fk_transactions_to_account', 'transactions', 'accounts', ['to_account_id'], ['id'])
    op.create_foreign_key('fk_transactions_related', 'transactions', 'transactions', ['related_transaction_id'], ['id'])
    
    # Change existing amount column to DECIMAL precision
    op.alter_column('transactions', 'amount', type_=sa.DECIMAL(precision=15, scale=2))
    
    # Add database constraints for data integrity
    op.create_check_constraint('positive_amount', 'transactions', 'amount > 0')
    
    # XOR constraint: exactly one of account_id, credit_card_id, or transfer pair must be set
    op.create_check_constraint(
        'single_transaction_target', 
        'transactions',
        '''(
            CASE WHEN account_id IS NOT NULL THEN 1 ELSE 0 END +
            CASE WHEN credit_card_id IS NOT NULL THEN 1 ELSE 0 END +
            CASE WHEN (from_account_id IS NOT NULL AND to_account_id IS NOT NULL) THEN 1 ELSE 0 END
        ) = 1'''
    )
    
    # Prevent self-transfers
    op.create_check_constraint(
        'no_self_transfer',
        'transactions', 
        'from_account_id IS NULL OR to_account_id IS NULL OR from_account_id != to_account_id'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop constraints first
    op.drop_constraint('no_self_transfer', 'transactions', type_='check')
    op.drop_constraint('single_transaction_target', 'transactions', type_='check') 
    op.drop_constraint('positive_amount', 'transactions', type_='check')
    
    # Drop foreign key constraints
    op.drop_constraint('fk_transactions_related', 'transactions', type_='foreignkey')
    op.drop_constraint('fk_transactions_to_account', 'transactions', type_='foreignkey')
    op.drop_constraint('fk_transactions_from_account', 'transactions', type_='foreignkey')
    
    # Drop new columns
    op.drop_column('transactions', 'related_transaction_id')
    op.drop_column('transactions', 'to_account_id')
    op.drop_column('transactions', 'from_account_id')
    op.drop_column('transactions', 'balance_impact')
    
    # Revert amount column to original type (Float)
    op.alter_column('transactions', 'amount', type_=sa.Float())
