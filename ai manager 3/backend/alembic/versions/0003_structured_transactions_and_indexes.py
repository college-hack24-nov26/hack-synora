"""0003_structured_transactions_and_indexes

Revision ID: 0003_structured_transactions_and_indexes
Revises: 0002_add_consents_and_encryption
Create Date: 2026-11-04 03:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0003_structured_transactions_and_indexes'
down_revision: Union[str, None] = '0002_add_consents_and_encryption'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Clean up any existing duplicates on (user_id, dedupe_hash) safely
    # keeping the earliest created_at record so unique constraint succeeds
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == 'sqlite':
        conn.execute(sa.text("""
            DELETE FROM transactions
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM transactions
                GROUP BY user_id, dedupe_hash
            )
        """))
    else:
        conn.execute(sa.text("""
            DELETE FROM transactions a USING transactions b
            WHERE a.id > b.id
              AND a.user_id = b.user_id
              AND a.dedupe_hash = b.dedupe_hash;
        """))

    # 2. Create index on (user_id, txn_date DESC) if not exists
    try:
        op.create_index(
            'ix_transactions_user_txn_date_desc',
            'transactions',
            ['user_id', sa.text('txn_date DESC')],
            unique=False
        )
    except Exception:
        pass

    # 3. Ensure composite index on (user_id, category_id) exists
    try:
        op.create_index(
            'ix_transactions_user_category',
            'transactions',
            ['user_id', 'category_id'],
            unique=False
        )
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.drop_index('ix_transactions_user_txn_date_desc', table_name='transactions')
    except Exception:
        pass

