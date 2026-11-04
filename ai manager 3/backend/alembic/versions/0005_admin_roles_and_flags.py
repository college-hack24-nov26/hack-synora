"""0005_admin_roles_and_flags

Revision ID: 0005_admin_roles_and_flags
Revises: 0004_add_needs_review_column
Create Date: 2026-11-04 04:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0005_admin_roles_and_flags'
down_revision: Union[str, None] = '0004_add_needs_review_column'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('users')]

    if 'role' not in columns:
        op.add_column(
            'users',
            sa.Column('role', sa.String(length=20), nullable=False, server_default='customer')
        )

    if 'is_active' not in columns:
        op.add_column(
            'users',
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1'))
        )

    if 'is_demo' not in columns:
        op.add_column(
            'users',
            sa.Column('is_demo', sa.Boolean(), nullable=False, server_default=sa.text('0'))
        )

    if 'segment' not in columns:
        op.add_column(
            'users',
            sa.Column('segment', sa.String(length=50), nullable=True)
        )


def downgrade() -> None:
    for col in ['segment', 'is_demo', 'is_active', 'role']:
        try:
            op.drop_column('users', col)
        except Exception:
            pass

