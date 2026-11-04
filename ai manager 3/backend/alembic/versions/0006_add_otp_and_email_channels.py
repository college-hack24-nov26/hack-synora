"""0006_add_otp_and_email_channels

Revision ID: 0006_add_otp_and_email_channels
Revises: 0005_admin_roles_and_flags
Create Date: 2026-11-04 05:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from app.models.custom_types import GUID, JSONType

revision: str = '0006_add_otp_and_email_channels'
down_revision: Union[str, None] = '0005_admin_roles_and_flags'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    user_columns = [col['name'] for col in inspector.get_columns('users')]

    if 'phone' not in user_columns:
        op.add_column('users', sa.Column('phone', sa.String(length=20), nullable=True))

    if 'phone_verified' not in user_columns:
        op.add_column('users', sa.Column('phone_verified', sa.Boolean(), nullable=False, server_default=sa.text('0')))

    if 'email_verified' not in user_columns:
        op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=False, server_default=sa.text('0')))

    if 'preferred_otp_channel' not in user_columns:
        op.add_column('users', sa.Column('preferred_otp_channel', sa.String(length=10), nullable=False, server_default='email'))

    if 'alert_preferences' not in user_columns:
        op.add_column('users', sa.Column('alert_preferences', JSONType(), nullable=False, server_default='{}'))

    tables = inspector.get_table_names()
    if 'otp_challenges' not in tables:
        op.create_table(
            'otp_challenges',
            sa.Column('id', GUID(), primary_key=True),
            sa.Column('user_id', GUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True),
            sa.Column('target', sa.String(length=255), nullable=False, index=True),
            sa.Column('channel', sa.String(length=20), nullable=False),
            sa.Column('code_hash', sa.String(length=64), nullable=False),
            sa.Column('purpose', sa.String(length=50), nullable=False),
            sa.Column('meta_data', JSONType(), nullable=False, server_default='{}'),
            sa.Column('attempts', sa.Integer(), nullable=False, server_default=sa.text('0')),
            sa.Column('max_attempts', sa.Integer(), nullable=False, server_default=sa.text('5')),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('resend_available_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        )
        try:
            op.create_index('ix_otp_challenges_target_purpose', 'otp_challenges', ['target', 'purpose'])
            op.create_index('ix_otp_challenges_user_purpose', 'otp_challenges', ['user_id', 'purpose'])
        except Exception:
            pass


def downgrade() -> None:
    try:
        op.drop_table('otp_challenges')
    except Exception:
        pass

    for col in ['alert_preferences', 'preferred_otp_channel', 'email_verified', 'phone_verified', 'phone']:
        try:
            op.drop_column('users', col)
        except Exception:
            pass

