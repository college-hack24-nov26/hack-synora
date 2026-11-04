"""0002_add_consents_and_encryption

Revision ID: 0002_add_consents_and_encryption
Revises: 0001_initial_schema
Create Date: 2026-11-04 02:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from app.models.custom_types import GUID, EncryptedText

revision: str = '0002_add_consents_and_encryption'
down_revision: Union[str, None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create consents table
    op.create_table(
        'consents',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('user_id', GUID(), nullable=False),
        sa.Column('consent_type', sa.String(length=50), nullable=False),
        sa.Column('granted', sa.Boolean(), server_default=sa.text('1'), nullable=False),
        sa.Column('granted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('policy_version', sa.String(length=20), server_default='1.0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'consent_type', name='uq_user_consent_type')
    )
    op.create_index(op.f('ix_consents_user_id'), 'consents', ['user_id'], unique=False)
    op.create_index('ix_consents_user_type', 'consents', ['user_id', 'consent_type'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_consents_user_type', table_name='consents')
    op.drop_index(op.f('ix_consents_user_id'), table_name='consents')
    op.drop_table('consents')

