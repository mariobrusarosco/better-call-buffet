"""Enhance balance points with comprehensive tracking

Revision ID: b5d8f3e9a2c7
Revises: a9f7e2b1c8d6
Create Date: 2025-07-23 13:30:00.000000

"""
from typing import Sequence, Union
from decimal import Decimal

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5d8f3e9a2c7'
down_revision: Union[str, None] = 'a9f7e2b1c8d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Step 1: Add new tracking columns
    op.add_column('balance_points', sa.Column('available_balance', sa.DECIMAL(precision=15, scale=2), nullable=True))
    op.add_column('balance_points', sa.Column('snapshot_type', sa.String(), nullable=True))
    op.add_column('balance_points', sa.Column('source_transaction_id', sa.UUID(), nullable=True))
    op.add_column('balance_points', sa.Column('is_verified', sa.Boolean(), nullable=True))
    op.add_column('balance_points', sa.Column('credit_card_id', sa.UUID(), nullable=True))
    
    # Step 2: Add foreign key constraints
    op.create_foreign_key('fk_balance_points_source_transaction', 'balance_points', 'transactions', ['source_transaction_id'], ['id'])
    op.create_foreign_key('fk_balance_points_credit_card', 'balance_points', 'credit_cards', ['credit_card_id'], ['id'], ondelete='CASCADE')
    
    # Step 3: Convert existing balance column from Float to DECIMAL
    op.alter_column('balance_points', 'balance',
                   existing_type=sa.Float(),
                   type_=sa.DECIMAL(precision=15, scale=2),
                   existing_nullable=False,
                   nullable=False)
    
    # Step 4: Initialize new columns with defaults for existing records
    # Set snapshot_type to 'manual' for existing balance points
    op.execute("UPDATE balance_points SET snapshot_type = 'manual' WHERE snapshot_type IS NULL")
    
    # Set is_verified to false for existing balance points
    op.execute("UPDATE balance_points SET is_verified = false WHERE is_verified IS NULL")
    
    # Step 5: Make required columns NOT NULL after initialization
    op.alter_column('balance_points', 'snapshot_type', nullable=False)
    op.alter_column('balance_points', 'is_verified', nullable=False)
    
    # Step 6: Modify account_id to be nullable (since we now support credit cards too)
    op.alter_column('balance_points', 'account_id', nullable=True)
    
    # Step 7: Add database constraints
    op.create_check_constraint('balance_precision', 'balance_points',
                              'balance >= -999999999999999.99 AND balance <= 999999999999999.99')
    
    op.create_check_constraint('available_balance_precision', 'balance_points',
                              'available_balance IS NULL OR (available_balance >= -999999999999999.99 AND available_balance <= 999999999999999.99)')
    
    # XOR constraint: exactly one of account_id or credit_card_id must be set
    op.create_check_constraint('single_balance_target', 'balance_points',
                              '''(
                                  CASE WHEN account_id IS NOT NULL THEN 1 ELSE 0 END +
                                  CASE WHEN credit_card_id IS NOT NULL THEN 1 ELSE 0 END
                              ) = 1''')
    
    # Valid snapshot types constraint
    op.create_check_constraint('valid_snapshot_type', 'balance_points',
                              "snapshot_type IN ('daily', 'transaction', 'manual', 'reconciliation')")
    
    # Step 8: Add performance indexes
    op.create_index('ix_balance_points_credit_card_id', 'balance_points', ['credit_card_id'])
    op.create_index('ix_balance_points_snapshot_type', 'balance_points', ['snapshot_type'])
    op.create_index('ix_balance_points_user_date', 'balance_points', ['user_id', 'date'])
    op.create_index('ix_balance_points_verified', 'balance_points', ['is_verified'])
    op.create_index('ix_balance_points_source_transaction', 'balance_points', ['source_transaction_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index('ix_balance_points_source_transaction', 'balance_points')
    op.drop_index('ix_balance_points_verified', 'balance_points')
    op.drop_index('ix_balance_points_user_date', 'balance_points')
    op.drop_index('ix_balance_points_snapshot_type', 'balance_points')
    op.drop_index('ix_balance_points_credit_card_id', 'balance_points')
    
    # Drop constraints
    op.drop_constraint('valid_snapshot_type', 'balance_points', type_='check')
    op.drop_constraint('single_balance_target', 'balance_points', type_='check')
    op.drop_constraint('available_balance_precision', 'balance_points', type_='check')
    op.drop_constraint('balance_precision', 'balance_points', type_='check')
    
    # Drop foreign key constraints
    op.drop_constraint('fk_balance_points_credit_card', 'balance_points', type_='foreignkey')
    op.drop_constraint('fk_balance_points_source_transaction', 'balance_points', type_='foreignkey')
    
    # Revert account_id to NOT NULL
    op.alter_column('balance_points', 'account_id', nullable=False)
    
    # Revert balance column to Float
    op.alter_column('balance_points', 'balance',
                   existing_type=sa.DECIMAL(precision=15, scale=2),
                   type_=sa.Float(),
                   existing_nullable=False,
                   nullable=False)
    
    # Drop new columns
    op.drop_column('balance_points', 'credit_card_id')
    op.drop_column('balance_points', 'is_verified')
    op.drop_column('balance_points', 'source_transaction_id')
    op.drop_column('balance_points', 'snapshot_type')
    op.drop_column('balance_points', 'available_balance')