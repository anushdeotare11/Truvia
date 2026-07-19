"""add live_sessions and live_session_turns (Module 5: Live Scam Interceptor §5)

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-19 22:40:00.000000

Two new tables backing the stateful, turn-by-turn Live Scam Interceptor. Follows
the established schema conventions: UUID PKs via gen_random_uuid(), timestamptz,
CHECK-constraint enums (not native enums), ON DELETE RESTRICT by default with
the documented CASCADE (turns) / SET NULL (linked case) exceptions.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'live_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.Text(), server_default='active', nullable=False),
        sa.Column('current_severity_band', sa.Text(), server_default='low', nullable=False),
        sa.Column('current_score', sa.SmallInteger(), server_default='0', nullable=False),
        sa.Column('scam_category', sa.Text(), nullable=True),
        sa.Column('intervention_shown_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('linked_case_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['linked_case_id'], ['cases.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('active','ended','escalated')", name='ck_live_sessions_status'),
        sa.CheckConstraint(
            "current_severity_band IN ('low','moderate','high','critical')",
            name='ck_live_sessions_severity_band',
        ),
        sa.CheckConstraint('current_score BETWEEN 0 AND 100', name='ck_live_sessions_current_score'),
    )
    op.create_index('idx_live_sessions_user_id', 'live_sessions', ['user_id'], unique=False)
    # Partial index for "resume active session" lookups.
    op.create_index(
        'idx_live_sessions_status',
        'live_sessions',
        ['status'],
        unique=False,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        'live_session_turns',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('turn_index', sa.Integer(), nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=False),
        sa.Column('turn_score', sa.SmallInteger(), nullable=False),
        sa.Column('cumulative_score', sa.SmallInteger(), nullable=False),
        sa.Column('flagged_phrases_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['live_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'turn_index', name='uq_live_session_turns_session_turn'),
        sa.CheckConstraint('turn_score BETWEEN 0 AND 100', name='ck_live_session_turns_turn_score'),
        sa.CheckConstraint('cumulative_score BETWEEN 0 AND 100', name='ck_live_session_turns_cumulative_score'),
    )
    op.create_index('idx_live_session_turns_session_id', 'live_session_turns', ['session_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_live_session_turns_session_id', table_name='live_session_turns')
    op.drop_table('live_session_turns')
    op.drop_index('idx_live_sessions_status', table_name='live_sessions')
    op.drop_index('idx_live_sessions_user_id', table_name='live_sessions')
    op.drop_table('live_sessions')
