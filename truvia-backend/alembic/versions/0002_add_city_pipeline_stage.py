"""add city and pipeline_stage columns to reports

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('reports', sa.Column('city', sa.String(length=100), nullable=True))
    op.add_column('reports', sa.Column('pipeline_stage', sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column('reports', 'pipeline_stage')
    op.drop_column('reports', 'city')
