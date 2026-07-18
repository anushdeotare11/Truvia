"""add fraud_rings and fraud_ring_members (Threat Intelligence Engine ring persistence)

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-17 00:45:00.000000

Persists detected fraud rings (Louvain communities) to Postgres so the Threat
Intelligence Engine works with or without Neo4j online. Mirrors the Neo4j
:Ring node and (:Entity)-[:MEMBER_OF]->(:Ring) edge (Backend_Schema §9.1/§9.2).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'fraud_rings',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('neo4j_ring_id', sa.String(length=100), nullable=False),
        sa.Column('algorithm', sa.String(length=50), server_default='python_louvain', nullable=False),
        sa.Column('algorithm_version', sa.String(length=50), server_default='v1', nullable=False),
        sa.Column('member_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('complaint_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('dominant_category', sa.String(length=100), nullable=True),
        sa.Column('aggregate_risk_score', sa.Numeric(precision=5, scale=2), server_default='0', nullable=False),
        sa.Column('risk_tier', sa.String(length=50), server_default='low', nullable=False),
        sa.Column('first_activity_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('detected_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('neo4j_ring_id', name='uq_fraud_rings_neo4j_ring_id'),
    )
    op.create_index('idx_fraud_rings_risk_tier', 'fraud_rings', ['risk_tier'], unique=False)

    op.create_table(
        'fraud_ring_members',
        sa.Column('ring_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('membership_confidence', sa.Numeric(precision=4, scale=3), server_default='1.0', nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['ring_id'], ['fraud_rings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('ring_id', 'entity_id'),
    )
    op.create_index('idx_fraud_ring_members_entity', 'fraud_ring_members', ['entity_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_fraud_ring_members_entity', table_name='fraud_ring_members')
    op.drop_table('fraud_ring_members')
    op.drop_index('idx_fraud_rings_risk_tier', table_name='fraud_rings')
    op.drop_table('fraud_rings')
