"""0004_add_needs_review_column

Revision ID: 0004_add_needs_review_column
Revises: 0003_structured_transactions_and_indexes
Create Date: 2026-11-04 04:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0004_add_needs_review_column'
down_revision: Union[str, None] = '0003_structured_transactions_and_indexes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('transactions')]
    
    if 'needs_review' not in columns:
        op.add_column(
            'transactions',
            sa.Column('needs_review', sa.Boolean(), nullable=False, server_default=sa.text('0'))
        )

    try:
        op.create_index(
            'ix_transactions_user_needs_review',
            'transactions',
            ['user_id', 'needs_review'],
            unique=False
        )
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.drop_index('ix_transactions_user_needs_review', table_name='transactions')
    except Exception:
        pass
    try:
        op.drop_column('transactions', 'needs_review')
    except Exception:
        pass

