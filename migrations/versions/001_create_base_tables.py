"""Create base tables

Revision ID: 001_create_base_tables
Revises: 
Create Date: 2025-07-26 22:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '001_create_base_tables'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table first (no dependencies)
    op.create_table('users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_email_unique', 'users', ['email'], unique=True)
    op.create_index('ix_users_created_at', 'users', ['created_at'])

    # Create brokers table (depends on users)
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

    # Create accounts table (depends on users and brokers)
    op.create_table('accounts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('currency', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('balance', sa.DECIMAL(15, 2), nullable=False),
        sa.Column('available_balance', sa.DECIMAL(15, 2), nullable=False),
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

    # Create credit_cards table (depends on accounts, brokers, users)
    op.create_table('credit_cards',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('last_four_digits', sa.String(length=4), nullable=False),
        sa.Column('brand', sa.String(), nullable=False),
        sa.Column('credit_limit', sa.DECIMAL(15, 2), nullable=False),
        sa.Column('current_balance', sa.DECIMAL(15, 2), nullable=False),
        sa.Column('available_credit', sa.DECIMAL(15, 2), nullable=False),
        sa.Column('due_date', sa.Integer(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('balance_updated_at', sa.DateTime(), nullable=False),
        sa.Column('account_id', sa.UUID(), nullable=False),
        sa.Column('broker_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id']),
        sa.ForeignKeyConstraint(['broker_id'], ['brokers.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_credit_cards_id', 'credit_cards', ['id'])
    op.create_index('ix_credit_cards_account', 'credit_cards', ['account_id'])
    op.create_index('ix_credit_cards_broker', 'credit_cards', ['broker_id'])
    op.create_index('ix_credit_cards_name', 'credit_cards', ['name'])
    op.create_index('ix_credit_cards_brand', 'credit_cards', ['brand'])
    op.create_index('ix_credit_cards_active', 'credit_cards', ['is_active'])

    # Create transactions table (depends on accounts)
    op.create_table('transactions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('amount', sa.DECIMAL(15, 2), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('is_income', sa.Boolean(), nullable=False),
        sa.Column('balance_impact', sa.String(), nullable=False),
        sa.Column('account_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_transactions_id', 'transactions', ['id'])

    # Create statements table
    op.create_table('statements',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('account_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('period_start', sa.DateTime(), nullable=True),
        sa.Column('period_end', sa.DateTime(), nullable=True),
        sa.Column('total_amount', sa.Float(), nullable=True),
        sa.Column('processed', sa.Boolean(), nullable=False, default=False),
        sa.Column('raw_content', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_statements_id', 'statements', ['id'])

    # Create invoices table
    op.create_table('invoices',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('credit_card_id', sa.UUID(), nullable=False),
        sa.Column('broker_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('raw_content', sa.JSON(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['broker_id'], ['brokers.id']),
        sa.ForeignKeyConstraint(['credit_card_id'], ['credit_cards.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_invoices_id', 'invoices', ['id'])
    op.create_index('ix_invoices_broker_id', 'invoices', ['broker_id'])
    op.create_index('ix_invoices_credit_card_id', 'invoices', ['credit_card_id'])
    op.create_index('ix_invoices_user_id', 'invoices', ['user_id'])
    op.create_index('ix_invoices_created_at', 'invoices', ['created_at'])

    # Create balance_points table
    op.create_table('balance_points',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('account_id', sa.UUID(), nullable=True),
        sa.Column('credit_card_id', sa.UUID(), nullable=True),
        sa.Column('balance', sa.DECIMAL(15, 2), nullable=False),
        sa.Column('available_balance', sa.DECIMAL(15, 2), nullable=True),
        sa.Column('snapshot_type', sa.String(), nullable=False),
        sa.Column('source_transaction_id', sa.UUID(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id']),
        sa.ForeignKeyConstraint(['credit_card_id'], ['credit_cards.id']),
        sa.ForeignKeyConstraint(['source_transaction_id'], ['transactions.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_balance_points_id', 'balance_points', ['id'])
    op.create_index('ix_balance_points_account_id', 'balance_points', ['account_id'])
    op.create_index('ix_balance_points_credit_card_id', 'balance_points', ['credit_card_id'])
    op.create_index('ix_balance_points_date', 'balance_points', ['date'])
    op.create_index('ix_balance_points_snapshot_type', 'balance_points', ['snapshot_type'])
    op.create_index('ix_balance_points_user_date', 'balance_points', ['user_id', 'date'])


def downgrade() -> None:
    op.drop_table('balance_points')
    op.drop_table('invoices')
    op.drop_table('statements')
    op.drop_table('transactions')
    op.drop_table('credit_cards')
    op.drop_table('accounts')
    op.drop_table('brokers')
    op.drop_table('users')