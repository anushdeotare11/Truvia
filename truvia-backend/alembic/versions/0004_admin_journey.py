"""add password_reset_tokens and knowledge_base.times_cited (Admin Journey §8)

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-17 01:50:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'knowledge_base',
        sa.Column('times_cited', sa.Integer(), server_default='0', nullable=False),
    )
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token_hash', sa.Text(), nullable=False),
        sa.Column('issued_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['issued_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash', name='uq_password_reset_tokens_token_hash'),
    )
    op.create_index('idx_password_reset_tokens_user', 'password_reset_tokens', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_password_reset_tokens_user', table_name='password_reset_tokens')
    op.drop_table('password_reset_tokens')
    op.drop_column('knowledge_base', 'times_cited')
