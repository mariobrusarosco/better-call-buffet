"""Enhance credit card model with decimal balance and tracking

Revision ID: a9f7e2b1c8d6
Revises: f8b2c1a3d4e5
Create Date: 2025-07-23 13:25:00.000000

"""
from typing import Sequence, Union
from decimal import Decimal

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9f7e2b1c8d6'
down_revision: Union[str, None] = 'f8b2c1a3d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Step 1: Add new balance tracking columns
    op.add_column('credit_cards', sa.Column('current_balance', sa.DECIMAL(precision=15, scale=2), nullable=True))
    op.add_column('credit_cards', sa.Column('available_credit', sa.DECIMAL(precision=15, scale=2), nullable=True))
    op.add_column('credit_cards', sa.Column('last_transaction_id', sa.UUID(), nullable=True))
    op.add_column('credit_cards', sa.Column('balance_updated_at', sa.DateTime(), nullable=True))
    
    # Step 2: Add foreign key constraint for last_transaction_id
    op.create_foreign_key('fk_credit_cards_last_transaction', 'credit_cards', 'transactions', ['last_transaction_id'], ['id'])
    
    # Step 3: Convert existing credit_limit column from Float to DECIMAL
    # First, handle any NULL credit limits
    op.execute("UPDATE credit_cards SET credit_limit = 0.0 WHERE credit_limit IS NULL")
    
    # Convert credit_limit column to DECIMAL
    op.alter_column('credit_cards', 'credit_limit',
                   existing_type=sa.Float(),
                   type_=sa.DECIMAL(precision=15, scale=2),
                   existing_nullable=True,
                   nullable=True)
    
    # Step 4: Initialize current_balance and available_credit
    # Set current_balance to 0.00 for all existing cards
    op.execute("UPDATE credit_cards SET current_balance = 0.00")
    
    # Calculate available_credit as credit_limit - current_balance (where credit_limit is not null)
    op.execute("""
        UPDATE credit_cards 
        SET available_credit = CASE 
            WHEN credit_limit IS NOT NULL THEN credit_limit - current_balance 
            ELSE NULL 
        END
    """)
    
    # Initialize balance_updated_at with created_at
    op.execute("UPDATE credit_cards SET balance_updated_at = created_at")
    
    # Step 5: Make current_balance and balance_updated_at NOT NULL after initialization
    op.alter_column('credit_cards', 'current_balance', nullable=False)
    op.alter_column('credit_cards', 'balance_updated_at', nullable=False)
    
    # Step 6: Add database constraints
    op.create_check_constraint('credit_limit_precision', 'credit_cards',
                              'credit_limit IS NULL OR (credit_limit >= 0 AND credit_limit <= 999999999999999.99)')
    
    op.create_check_constraint('current_balance_precision', 'credit_cards',
                              'current_balance >= -999999999999999.99 AND current_balance <= 999999999999999.99')
    
    op.create_check_constraint('available_credit_precision', 'credit_cards',
                              'available_credit IS NULL OR (available_credit >= -999999999999999.99 AND available_credit <= 999999999999999.99)')
    
    op.create_check_constraint('positive_credit_limit', 'credit_cards',
                              'credit_limit IS NULL OR credit_limit >= 0')
    
    # Step 7: Add performance indexes
    op.create_index('ix_credit_cards_current_balance', 'credit_cards', ['current_balance'])
    op.create_index('ix_credit_cards_balance_updated', 'credit_cards', ['balance_updated_at'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index('ix_credit_cards_balance_updated', 'credit_cards')
    op.drop_index('ix_credit_cards_current_balance', 'credit_cards')
    
    # Drop constraints
    op.drop_constraint('positive_credit_limit', 'credit_cards', type_='check')
    op.drop_constraint('available_credit_precision', 'credit_cards', type_='check')
    op.drop_constraint('current_balance_precision', 'credit_cards', type_='check')
    op.drop_constraint('credit_limit_precision', 'credit_cards', type_='check')
    
    # Drop foreign key constraint
    op.drop_constraint('fk_credit_cards_last_transaction', 'credit_cards', type_='foreignkey')
    
    # Revert credit_limit column to Float
    op.alter_column('credit_cards', 'credit_limit',
                   existing_type=sa.DECIMAL(precision=15, scale=2),
                   type_=sa.Float(),
                   existing_nullable=True,
                   nullable=True)
    
    # Drop new columns
    op.drop_column('credit_cards', 'balance_updated_at')
    op.drop_column('credit_cards', 'last_transaction_id')
    op.drop_column('credit_cards', 'available_credit')
    op.drop_column('credit_cards', 'current_balance')