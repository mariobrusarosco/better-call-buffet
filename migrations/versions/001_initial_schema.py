"""Initial schema - clean baseline

Revision ID: 001_initial_schema
Revises: 
Create Date: 2025-08-02 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables in correct dependency order."""
    
    # Step 1: Create users table (no dependencies)
    op.create_table('users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_email_unique', 'users', ['email'], unique=True)
    op.create_index('ix_users_created_at', 'users', ['created_at'])

    # Step 2: Create brokers table (depends on users)
    op.create_table('brokers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('colors', sa.ARRAY(sa.String()), nullable=False),
        sa.Column('logo', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_brokers_id', 'brokers', ['id'])

    # Step 3: Create accounts table (depends on users and brokers, but NOT transactions yet)
    op.create_table('accounts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('currency', sa.String(), nullable=False, default='BRL'),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('balance', sa.DECIMAL(precision=15, scale=2), nullable=False, default=0.00),
        sa.Column('available_balance', sa.DECIMAL(precision=15, scale=2), nullable=False, default=0.00),
        sa.Column('last_transaction_id', sa.UUID(), nullable=True),  # FK will be added later
        sa.Column('balance_updated_at', sa.DateTime(), nullable=False),
        sa.Column('broker_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint('balance = ROUND(balance, 2)', name='balance_precision'),
        sa.ForeignKeyConstraint(['broker_id'], ['brokers.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_accounts_id', 'accounts', ['id'])
    op.create_index('ix_accounts_type', 'accounts', ['type'])
    op.create_index('ix_accounts_user_id', 'accounts', ['user_id'])

    # Step 4: Create credit_cards table (depends on accounts and brokers)
    op.create_table('credit_cards',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('brand', sa.String(), nullable=False),
        sa.Column('last_four_digits', sa.String(length=4), nullable=True),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('credit_limit', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('available_credit', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('current_balance', sa.DECIMAL(precision=15, scale=2), nullable=False, default=0.00),
        sa.Column('last_transaction_id', sa.UUID(), nullable=True),  # FK will be added later
        sa.Column('balance_updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('account_id', sa.UUID(), nullable=False),
        sa.Column('broker_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id']),
        sa.ForeignKeyConstraint(['broker_id'], ['brokers.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'broker_id', 'account_id', name='uix_name_broker_account')
    )
    op.create_index('ix_credit_cards_id', 'credit_cards', ['id'])
    op.create_index('ix_credit_cards_account', 'credit_cards', ['account_id'])
    op.create_index('ix_credit_cards_active', 'credit_cards', ['is_active'])
    op.create_index('ix_credit_cards_balance_updated', 'credit_cards', ['balance_updated_at'])
    op.create_index('ix_credit_cards_brand', 'credit_cards', ['brand'])
    op.create_index('ix_credit_cards_broker', 'credit_cards', ['broker_id'])
    op.create_index('ix_credit_cards_credit_limit', 'credit_cards', ['credit_limit'])
    op.create_index('ix_credit_cards_current_balance', 'credit_cards', ['current_balance'])
    op.create_index('ix_credit_cards_deleted', 'credit_cards', ['is_deleted'])
    op.create_index('ix_credit_cards_due_date', 'credit_cards', ['due_date'])
    op.create_index('ix_credit_cards_last_four', 'credit_cards', ['last_four_digits'])
    op.create_index('ix_credit_cards_name', 'credit_cards', ['name'])

    # Step 5: Create transactions table (depends on accounts, credit_cards, brokers)
    op.create_table('transactions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('amount', sa.DECIMAL(precision=15, scale=2), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('movement_type', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('balance_impact', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('account_id', sa.UUID(), nullable=True),
        sa.Column('credit_card_id', sa.UUID(), nullable=True),
        sa.Column('from_account_id', sa.UUID(), nullable=True),
        sa.Column('to_account_id', sa.UUID(), nullable=True),
        sa.Column('related_transaction_id', sa.UUID(), nullable=True),
        sa.Column('broker_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('is_paid', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id']),
        sa.ForeignKeyConstraint(['broker_id'], ['brokers.id']),
        sa.ForeignKeyConstraint(['credit_card_id'], ['credit_cards.id']),
        sa.ForeignKeyConstraint(['from_account_id'], ['accounts.id']),
        sa.ForeignKeyConstraint(['related_transaction_id'], ['transactions.id']),
        sa.ForeignKeyConstraint(['to_account_id'], ['accounts.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_transactions_id', 'transactions', ['id'])

    # Step 6: Add foreign key constraints that reference transactions
    op.create_foreign_key('fk_accounts_last_transaction', 'accounts', 'transactions', ['last_transaction_id'], ['id'])
    op.create_foreign_key('fk_credit_cards_last_transaction', 'credit_cards', 'transactions', ['last_transaction_id'], ['id'])

    # Step 7: Create remaining tables
    op.create_table('balance_points',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('account_id', sa.UUID(), nullable=True),
        sa.Column('credit_card_id', sa.UUID(), nullable=True),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('points', sa.DECIMAL(precision=15, scale=2), nullable=False),
        sa.Column('snapshot_type', sa.String(), nullable=False),
        sa.Column('source_transaction_id', sa.UUID(), nullable=True),
        sa.Column('note', sa.String(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['credit_card_id'], ['credit_cards.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_transaction_id'], ['transactions.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_balance_points_id', 'balance_points', ['id'])
    op.create_index('ix_balance_points_account_id', 'balance_points', ['account_id'])
    op.create_index('ix_balance_points_credit_card_id', 'balance_points', ['credit_card_id'])
    op.create_index('ix_balance_points_date', 'balance_points', ['date'])
    op.create_index('ix_balance_points_snapshot_type', 'balance_points', ['snapshot_type'])
    op.create_index('ix_balance_points_source_transaction', 'balance_points', ['source_transaction_id'])
    op.create_index('ix_balance_points_user_date', 'balance_points', ['user_id', 'date'])
    op.create_index('ix_balance_points_verified', 'balance_points', ['is_verified'])

    op.create_table('statements',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('account_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('period_start', sa.DateTime(), nullable=True),
        sa.Column('period_end', sa.DateTime(), nullable=True),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('total_due', sa.String(), nullable=True),
        sa.Column('min_payment', sa.String(), nullable=True),
        sa.Column('opening_balance', sa.String(), nullable=True),
        sa.Column('closing_balance', sa.String(), nullable=True),
        sa.Column('raw_statement', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('is_processed', sa.Boolean(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_statements_id', 'statements', ['id'])

    op.create_table('invoices',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('broker_id', sa.UUID(), nullable=False),
        sa.Column('credit_card_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('period_start', sa.DateTime(), nullable=True),
        sa.Column('period_end', sa.DateTime(), nullable=True),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('total_amount', sa.Float(), nullable=True),
        sa.Column('raw_invoice', sa.JSON(), nullable=False),
        sa.Column('is_paid', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['broker_id'], ['brokers.id']),
        sa.ForeignKeyConstraint(['credit_card_id'], ['credit_cards.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_invoices_id', 'invoices', ['id'])
    op.create_index('ix_invoices_broker_id', 'invoices', ['broker_id'])
    op.create_index('ix_invoices_created_at', 'invoices', ['created_at'])
    op.create_index('ix_invoices_credit_card_id', 'invoices', ['credit_card_id'])
    op.create_index('ix_invoices_user_id', 'invoices', ['user_id'])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('invoices')
    op.drop_table('statements')
    op.drop_table('balance_points')
    op.drop_constraint('fk_credit_cards_last_transaction', 'credit_cards', type_='foreignkey')
    op.drop_constraint('fk_accounts_last_transaction', 'accounts', type_='foreignkey')
    op.drop_table('transactions')
    op.drop_table('credit_cards')
    op.drop_table('accounts')
    op.drop_table('brokers')
    op.drop_table('users')