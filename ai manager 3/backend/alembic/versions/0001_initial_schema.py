"""0001_initial_schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-11-03 16:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from app.models.custom_types import GUID, JSONType

revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        'users',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('currency', sa.String(length=10), server_default='INR', nullable=False),
        sa.Column('timezone', sa.String(length=50), server_default='Asia/Kolkata', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 2. accounts
    op.create_table(
        'accounts',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('user_id', GUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('last4', sa.String(length=4), nullable=True),
        sa.Column('opening_balance_minor', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_accounts_user_id'), 'accounts', ['user_id'], unique=False)

    # 3. categories
    op.create_table(
        'categories',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('user_id', GUID(), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('parent_id', GUID(), nullable=True),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('color', sa.String(length=20), nullable=True),
        sa.Column('is_income', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['parent_id'], ['categories.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_categories_user_id'), 'categories', ['user_id'], unique=False)

    # 4. imports
    op.create_table(
        'imports',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('user_id', GUID(), nullable=False),
        sa.Column('source_type', sa.String(length=20), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='pending', nullable=False),
        sa.Column('total_rows', sa.Integer(), server_default='0', nullable=False),
        sa.Column('parsed_rows', sa.Integer(), server_default='0', nullable=False),
        sa.Column('failed_rows', sa.Integer(), server_default='0', nullable=False),
        sa.Column('error_report', JSONType(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_imports_user_id'), 'imports', ['user_id'], unique=False)

    # 5. transactions
    op.create_table(
        'transactions',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('user_id', GUID(), nullable=False),
        sa.Column('account_id', GUID(), nullable=False),
        sa.Column('amount_minor', sa.BigInteger(), nullable=False),
        sa.Column('direction', sa.String(length=10), nullable=False),
        sa.Column('currency', sa.String(length=10), server_default='INR', nullable=False),
        sa.Column('txn_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('merchant_raw', sa.Text(), nullable=True),
        sa.Column('merchant_normalized', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category_id', GUID(), nullable=True),
        sa.Column('category_source', sa.String(length=20), server_default='rule', nullable=False),
        sa.Column('category_confidence', sa.Numeric(precision=5, scale=4), server_default='1.0', nullable=False),
        sa.Column('source', sa.String(length=20), nullable=False),
        sa.Column('import_id', GUID(), nullable=True),
        sa.Column('dedupe_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['import_id'], ['imports.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'dedupe_hash', name='uq_user_dedupe_hash'),
    )
    op.create_index(op.f('ix_transactions_user_id'), 'transactions', ['user_id'], unique=False)
    op.create_index(op.f('ix_transactions_account_id'), 'transactions', ['account_id'], unique=False)
    op.create_index(op.f('ix_transactions_category_id'), 'transactions', ['category_id'], unique=False)
    op.create_index('ix_transactions_user_txn_date', 'transactions', ['user_id', 'txn_date'], unique=False)
    op.create_index('ix_transactions_user_category', 'transactions', ['user_id', 'category_id'], unique=False)

    # 6. merchant_rules
    op.create_table(
        'merchant_rules',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('user_id', GUID(), nullable=False),
        sa.Column('pattern', sa.String(length=255), nullable=False),
        sa.Column('category_id', GUID(), nullable=False),
        sa.Column('priority', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_merchant_rules_user_id'), 'merchant_rules', ['user_id'], unique=False)
    op.create_index('ix_merchant_rules_user_priority', 'merchant_rules', ['user_id', 'priority'], unique=False)

    # 7. budgets
    op.create_table(
        'budgets',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('user_id', GUID(), nullable=False),
        sa.Column('category_id', GUID(), nullable=False),
        sa.Column('month', sa.String(length=7), nullable=False),
        sa.Column('limit_minor', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'category_id', 'month', name='uq_user_category_month_budget'),
    )
    op.create_index(op.f('ix_budgets_user_id'), 'budgets', ['user_id'], unique=False)

    # 8. forecasts
    op.create_table(
        'forecasts',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('user_id', GUID(), nullable=False),
        sa.Column('target_month', sa.String(length=7), nullable=False),
        sa.Column('category_id', GUID(), nullable=True),
        sa.Column('predicted_minor', sa.BigInteger(), nullable=False),
        sa.Column('lower_bound_minor', sa.BigInteger(), nullable=False),
        sa.Column('upper_bound_minor', sa.BigInteger(), nullable=False),
        sa.Column('model_version', sa.String(length=50), server_default='v1-stat', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_forecasts_user_id'), 'forecasts', ['user_id'], unique=False)

    # 9. savings_suggestions
    op.create_table(
        'savings_suggestions',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('user_id', GUID(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('detail', sa.Text(), nullable=False),
        sa.Column('estimated_saving_minor', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('status', sa.String(length=20), server_default='new', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_savings_suggestions_user_id'), 'savings_suggestions', ['user_id'], unique=False)

    # 10. audit_log
    op.create_table(
        'audit_log',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('user_id', GUID(), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('entity', sa.String(length=100), nullable=False),
        sa.Column('entity_id', sa.String(length=36), nullable=True),
        sa.Column('meta_data', JSONType(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_audit_log_user_id'), 'audit_log', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_table('audit_log')
    op.drop_table('savings_suggestions')
    op.drop_table('forecasts')
    op.drop_table('budgets')
    op.drop_table('merchant_rules')
    op.drop_table('transactions')
    op.drop_table('imports')
    op.drop_table('categories')
    op.drop_table('accounts')
    op.drop_table('users')

